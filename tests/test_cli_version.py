"""Tests for the charlie CLI --version / -v flag."""

from typer.testing import CliRunner

from charlieverse.cli.main import app

runner = CliRunner()


def test_version_long_flag():
    """charlie --version prints package version and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "charlieverse" in result.output


def test_version_short_flag():
    """charlie -v prints package version and exits 0."""
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert "charlieverse" in result.output


def test_version_output_format():
    """charlie --version output matches 'charlieverse X.Y.Z' format."""
    result = runner.invoke(app, ["--version"])
    # Output should be "charlieverse <version>"
    parts = result.output.strip().split()
    assert parts[0] == "charlieverse"
    # Version string should look like semver (digits with dots)
    assert "." in parts[1]
