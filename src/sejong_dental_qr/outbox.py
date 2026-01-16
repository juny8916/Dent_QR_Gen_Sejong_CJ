"""
outbox 생성 모듈(운영자 전달용 ZIP 묶음).

- 무엇(What): NEW/REACTIVATED 치과만 모아 output/outbox/zips/*.zip을 만든다.
- 왜(Why): 운영자가 변경된 치과에만 빠르게 전달할 수 있도록 하기 위함.
- 어떻게(How): delivery 폴더의 qr.png/qr_named.png/info.txt를 ZIP으로 포장한다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
import zipfile
from typing import Iterable

from .config import AppConfig
from .planner import ChangeRecord
from .report import MappingRecord
from .utils import slugify_name


# sendlist.csv 고정 컬럼(운영자 전달 리스트용).
SENDLIST_COLUMNS = [
    "clinic_id",
    "clinic_name",
    "change_type",
    "url",
    "zip_path",
]


@dataclass(frozen=True)
class OutboxResult:
    targets: int
    zips_created: int
    sendlist_path: Path


# -----------------------------------------------------------------------------
# [WHY] 변경 대상만 선별하여 전달 비용/노력을 줄인다.
# [WHAT] sendlist.csv + zips/*.zip 생성.
# [HOW] ChangeRecord 중 NEW/REACTIVATED만 선택, 누락 파일은 스킵(경고 로그).
# -----------------------------------------------------------------------------
def create_outbox(
    cfg: AppConfig,
    mapping_records: Iterable[MappingRecord],
    changes: Iterable[ChangeRecord],
) -> OutboxResult:
    if cfg.outbox_mode != "changed":
        raise ValueError(f"Unsupported outbox_mode: {cfg.outbox_mode}")

    outbox_root = Path(cfg.outbox_root)
    if outbox_root.exists():
        shutil.rmtree(outbox_root)
    zips_root = outbox_root / "zips"
    zips_root.mkdir(parents=True, exist_ok=True)

    mapping_by_id = {record.clinic_id: record for record in mapping_records}
    changes_list = list(changes)
    targets = [
        change
        for change in changes_list
        if change.change_type in {"NEW", "REACTIVATED"}
    ]

    sendlist_rows: list[list[str]] = []
    zip_count = 0
    for change in targets:
        record = mapping_by_id.get(change.clinic_id)
        if record is None:
            logging.warning("Missing mapping for clinic_id=%s", change.clinic_id)
            continue
        if str(record.status).upper() != "ACTIVE":
            logging.warning("Outbox skip inactive clinic_id=%s", change.clinic_id)
            continue

        slug = slugify_name(record.clinic_name)
        delivery_dir = Path(cfg.output_root) / "delivery" / f"{record.clinic_id}_{slug}"
        required_files = [
            delivery_dir / "qr.png",
            delivery_dir / "qr_named.png",
            delivery_dir / "info.txt",
        ]
        missing = [path.name for path in required_files if not path.exists()]
        if missing:
            logging.warning(
                "Outbox skip clinic_id=%s missing files: %s",
                record.clinic_id,
                ", ".join(missing),
            )
            continue

        zip_path = zips_root / f"{record.clinic_id}_{slug}.zip"
        _write_zip(zip_path, required_files)
        zip_count += 1

        sendlist_rows.append(
            [
                record.clinic_id,
                record.clinic_name,
                change.change_type,
                record.url,
                str(zip_path),
            ]
        )

    sendlist_path = outbox_root / "sendlist.csv"
    _write_sendlist(sendlist_path, sendlist_rows)
    return OutboxResult(targets=len(targets), zips_created=zip_count, sendlist_path=sendlist_path)


def _write_zip(zip_path: Path, files: Iterable[Path]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in files:
            zip_file.write(path, arcname=path.name)


def _write_sendlist(path: Path, rows: Iterable[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(SENDLIST_COLUMNS)
        for row in rows:
            writer.writerow(row)
