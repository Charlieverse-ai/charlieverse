"""Charlieverse embedding service."""

from charlieverse.embeddings.service import (
    EMBEDDING_DIM,
    encode,
    encode_one,
    prepare_entity_text,
    prepare_knowledge_text,
    prepare_session_text,
)

__all__ = [
    "EMBEDDING_DIM",
    "encode",
    "encode_one",
    "prepare_entity_text",
    "prepare_knowledge_text",
    "prepare_session_text",
]
