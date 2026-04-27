"""Entity extraction from text using spaCy NER + keyword extraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from spacy.language import Language

from charlieverse.config import config
from charlieverse.types.dates import UTCDatetime, utc_now
from charlieverse.types.strings import CleanedText

logger = logging.getLogger(__name__)


_nlp: Language | None = None

_MODEL_NAME = "en_core_web_sm"
_MODEL_VERSION = "3.8.0"
_MODEL_URL = f"https://github.com/explosion/spacy-models/releases/download/{_MODEL_NAME}-{_MODEL_VERSION}/{_MODEL_NAME}-{_MODEL_VERSION}-py3-none-any.whl"

# Entity labels worth extracting for memory search
_RELEVANT_LABELS = {"PERSON", "PRODUCT", "GPE", "EVENT", "WORK_OF_ART", "FAC", "NORP", "LOC", "TIME", "MISC", "PROD", "DRV", "PER"}

# Temporal expressions that imply date ranges
_RANGE_KEYWORDS = {
    "week": 7,
    "month": 30,
    "year": 365,
    "quarter": 90,
}


@dataclass
class TemporalRef:
    """A resolved temporal reference with a date range."""

    text: str
    start: UTCDatetime
    end: UTCDatetime


def _model_dir() -> Path:
    """Persistent model directory outside uv's environment."""
    return config.path / "models"


def _model_path() -> Path:
    """Path to the extracted spaCy model."""
    return _model_dir() / _MODEL_NAME / f"{_MODEL_NAME}-{_MODEL_VERSION}"


def _ensure_model() -> Path:
    """Download and extract the spaCy model if not already present."""
    path = _model_path()
    if path.exists() and (path / "meta.json").exists():
        return path

    import io
    import urllib.request
    import zipfile

    logger.info("Downloading spaCy model %s-%s...", _MODEL_NAME, _MODEL_VERSION)
    dest = _model_dir()
    dest.mkdir(parents=True, exist_ok=True)

    # Download the wheel (it's a zip)
    with urllib.request.urlopen(_MODEL_URL) as resp:
        data = resp.read()

    # Extract only the model package (skip dist-info)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            if member.startswith(f"{_MODEL_NAME}/"):
                zf.extract(member, dest)

    if not path.exists():
        raise RuntimeError(f"Model extraction failed: {path} not found")

    logger.info("spaCy model installed to %s", path)
    return path


def _load_model() -> Language:
    from spacy import load

    path = _ensure_model()
    return load(path)


def prewarm_nlp():
    logger.info("Loading Vector Models")
    global _nlp
    _nlp = _load_model()
    logger.info("Vector Models Loaded")


def _get_nlp() -> Language | None:
    """Lazy-load the spaCy model. Returns None if unavailable."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = _load_model()
        except Exception:
            logger.exception("Failed to load spaCy model")
            return None
    return _nlp


def _resolve_date_range(text: str, now: UTCDatetime | None = None) -> TemporalRef | None:
    """Resolve a temporal expression to a UTC date range.

    Uses dateparser for the anchor point, then infers range width
    from keywords in the expression (week, month, year, etc.).
    """
    import dateparser

    anchor = now or utc_now()
    parsed = dateparser.parse(text, settings={"RELATIVE_BASE": anchor})
    if not parsed:
        return None

    # dateparser returns a tz-aware datetime in the same zone as RELATIVE_BASE.
    # Normalize to UTC for consistent comparisons.
    from datetime import UTC

    parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    # Determine range width from the expression
    text_lower = text.lower()
    range_days = 1  # default: single day (e.g. "yesterday")

    import calendar

    month_names = [m.lower() for m in calendar.month_name[1:]] + [m.lower() for m in calendar.month_abbr[1:]]
    is_month = any(m in text_lower for m in month_names if m)

    if is_month:
        start = parsed.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(start.year, start.month)[1]
        end = start.replace(day=last_day) + timedelta(days=1)
    else:
        for keyword, days in _RANGE_KEYWORDS.items():
            if keyword in text_lower:
                range_days = days
                break

        start = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=range_days)

    # Clamp end to now if it's in the future
    if end > anchor:
        end = anchor

    return TemporalRef(text=text, start=UTCDatetime(start), end=UTCDatetime(end))


def extract_keywords(text: CleanedText | None) -> list[str]:
    """Extract named entities and key noun phrases from text.

    Args:
        text: Input text to analyze.

    Returns:
        Deduplicated list of extracted terms, ordered by appearance.
    """
    if not text:
        return []

    content = str(text)
    nlp = _get_nlp()
    if nlp is None:
        return []

    doc = nlp(content)

    seen: set[str] = set()
    terms: list[str] = []

    for ent in doc.ents:
        if ent.label_ in _RELEVANT_LABELS:
            # split mutli word matches up into single word
            words = ent.text.strip().split(" ")
            for normalized in words:
                lower = normalized.lower()
                if lower not in seen and len(normalized) > 1:
                    seen.add(lower)
                    terms.append(normalized)
    return terms


def extract_temporal_refs(text: CleanedText | None) -> list[TemporalRef]:
    """Extract and resolve temporal references from text.

    Returns resolved date ranges for expressions like "last week",
    "yesterday", "in February", etc. Returns empty list if none found.
    """
    if not text:
        return []

    nlp = _get_nlp()
    if nlp is None:
        return []

    doc = nlp(str(text))

    refs: list[TemporalRef] = []
    now = utc_now()

    for ent in doc.ents:
        if ent.label_ == "DATE":
            ref = _resolve_date_range(ent.text, now=now)
            if ref:
                refs.append(ref)

    return refs
