"""Shared utility helpers."""

from __future__ import annotations

from slugify import slugify


def slugify_name(name: str, max_len: int = 40) -> str:
    value = slugify(name, max_length=max_len)
    return value if value else "clinic"
