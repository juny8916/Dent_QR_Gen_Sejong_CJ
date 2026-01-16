"""
CSV 리포트 생성 모듈(mapping/changes).

- 무엇(What): 운영자가 확인할 mapping.csv, changes.csv를 생성한다.
- 왜(Why): clinic_id/상태/URL/변경 유형을 운영자가 빠르게 확인하기 위함.
- 어떻게(How): Excel 호환을 위해 utf-8-sig로 저장한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable

from .planner import ChangeRecord


# mapping.csv 고정 컬럼(운영 리포트용).
MAPPING_COLUMNS = [
    "clinic_name",
    "clinic_id",
    "status",
    "address",
    "phone",
    "director",
    "homepage",
    "url",
    "page_path",
    "qr_path",
    "qr_named_path",
]

# changes.csv 고정 컬럼(변경 이력 리포트용).
CHANGES_COLUMNS = [
    "clinic_id",
    "clinic_name",
    "change_type",
    "notes",
]


@dataclass(frozen=True)
class MappingRecord:
    clinic_name: str
    clinic_id: str
    status: str
    address: str
    phone: str
    director: str
    homepage: str
    url: str
    page_path: str
    qr_path: str
    qr_named_path: str


# -----------------------------------------------------------------------------
# [WHY] 치과별 URL/QR 경로 등 운영 메타데이터를 표 형태로 제공한다.
# [WHAT] output/mapping.csv 생성.
# [HOW] MappingRecord를 고정 컬럼 순서로 기록(utf-8-sig).
# -----------------------------------------------------------------------------
def write_mapping_csv(records: Iterable[MappingRecord], path: str | Path) -> None:
    _write_csv(
        path,
        MAPPING_COLUMNS,
        (
            [
                _safe_str(record.clinic_name),
                _safe_str(record.clinic_id),
                _safe_str(record.status),
                _safe_str(record.address),
                _safe_str(record.phone),
                _safe_str(record.director),
                _safe_str(record.homepage),
                _safe_str(record.url),
                _safe_str(record.page_path),
                _safe_str(record.qr_path),
                _safe_str(record.qr_named_path),
            ]
            for record in records
        ),
    )


# -----------------------------------------------------------------------------
# [WHY] 신규/비활성/재활성화 등 변경 이력을 운영자가 추적할 수 있게 한다.
# [WHAT] output/changes.csv 생성.
# [HOW] ChangeRecord를 고정 컬럼 순서로 기록(utf-8-sig).
# -----------------------------------------------------------------------------
def write_changes_csv(
    changes: Iterable[ChangeRecord],
    path: str | Path,
    notes_by_id: dict[str, str] | None = None,
) -> None:
    notes_lookup = notes_by_id or {}
    _write_csv(
        path,
        CHANGES_COLUMNS,
        (
            [
                _safe_str(change.clinic_id),
                _safe_str(change.clinic_name),
                _safe_str(change.change_type),
                _safe_str(notes_lookup.get(change.clinic_id, "")),
            ]
            for change in changes
        ),
    )


def _write_csv(path: str | Path, columns: list[str], rows: Iterable[list[str]]) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)


def _safe_str(value: object) -> str:
    return "" if value is None else str(value)
