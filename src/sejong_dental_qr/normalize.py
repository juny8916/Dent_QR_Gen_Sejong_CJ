"""Name normalization helpers."""

from __future__ import annotations


def normalize_name(raw: str) -> str:
    """Strip edges and collapse internal whitespace to single spaces."""
    return " ".join(raw.strip().split())
