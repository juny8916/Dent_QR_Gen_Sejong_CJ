"""CSV report generation for mapping and changes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable

from .planner import ChangeRecord


MAPPING_COLUMNS = [
    "clinic_name",
    "clinic_id",
    "status",
    "url",
    "page_path",
    "qr_path",
]

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
    url: str
    page_path: str
    qr_path: str


def write_mapping_csv(records: Iterable[MappingRecord], path: str | Path) -> None:
    _write_csv(
        path,
        MAPPING_COLUMNS,
        (
            [
                _safe_str(record.clinic_name),
                _safe_str(record.clinic_id),
                _safe_str(record.status),
                _safe_str(record.url),
                _safe_str(record.page_path),
                _safe_str(record.qr_path),
            ]
            for record in records
        ),
    )


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
