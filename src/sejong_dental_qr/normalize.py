"""
치과명 정규화(name normalization) 모듈.

치과명은 clinic_id 동일성 키로 사용되므로, 공백/표기 흔들림을 제거해 일관성을 유지한다.
"""

from __future__ import annotations


def normalize_name(raw: str) -> str:
    """앞뒤 공백 제거 + 연속 공백 축약(치과명 동일성 유지용)."""
    return " ".join(raw.strip().split())
