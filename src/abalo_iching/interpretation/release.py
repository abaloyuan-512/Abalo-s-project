"""Repository-controlled narrative release gate; environment variables cannot promote it."""

from .models import NarrativeReleaseSnapshot


def narrative_release_snapshot() -> NarrativeReleaseSnapshot:
    return NarrativeReleaseSnapshot()
