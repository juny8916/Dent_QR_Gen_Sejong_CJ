"""
공용 유틸리티 모듈.

- 무엇(What): 파일/디렉토리 이름 생성 등 공통 처리.
- 왜(Why): delivery/outbox의 폴더명 규칙을 일관되게 유지하기 위함.
- 어떻게(How): slugify를 사용해 안정적인 ASCII 슬러그를 만든다.
"""

from __future__ import annotations

from slugify import slugify


def slugify_name(name: str, max_len: int = 40) -> str:
    """치과명 → 파일명/폴더명용 slug. 비어있으면 'clinic'으로 대체."""
    value = slugify(name, max_length=max_len)
    return value if value else "clinic"
