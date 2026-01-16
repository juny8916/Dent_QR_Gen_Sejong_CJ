"""
치과별 전달 패키지(delivery) 생성 모듈.

- 무엇(What): ACTIVE 치과마다 QR/정보 텍스트를 한 폴더에 모아 전달용으로 만든다.
- 왜(Why): 운영자가 각 치과에 전달할 파일을 바로 배포할 수 있게 하기 위함.
- 어떻게(How): output/qr/의 PNG를 복사하고 info.txt를 생성한다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import shutil
from typing import Iterable

from .config import AppConfig
from .report import MappingRecord
from .utils import slugify_name


@dataclass(frozen=True)
class DeliveryResult:
    output_dir: Path
    clinic_id: str
    clinic_name: str


# -----------------------------------------------------------------------------
# [WHY] ACTIVE 치과에 제공할 전달물(assets)을 규격화해 운영 편의성을 높인다.
# [WHAT] output/delivery/<clinic_id>_<slug>/ 아래에 qr.png, qr_named.png, info.txt 생성.
# [HOW] MappingRecord 기반으로 파일 복사 + 안내문 렌더링.
# -----------------------------------------------------------------------------
def create_delivery_packages(
    cfg: AppConfig,
    records: Iterable[MappingRecord],
    delivery_root: str | Path | None = None,
) -> list[DeliveryResult]:
    root = Path(delivery_root) if delivery_root is not None else Path(cfg.output_root) / "delivery"
    now = _now_iso()
    results: list[DeliveryResult] = []

    for record in records:
        if not _is_active(record.status):
            continue
        if not record.qr_path:
            raise ValueError(f"Missing qr_path for ACTIVE clinic: {record.clinic_id}")

        slug = slugify_name(record.clinic_name)
        target_dir = root / f"{record.clinic_id}_{slug}"
        target_dir.mkdir(parents=True, exist_ok=True)

        qr_source = Path(record.qr_path)
        qr_target = target_dir / "qr.png"
        shutil.copy2(qr_source, qr_target)

        if record.qr_named_path:
            named_source = Path(record.qr_named_path)
            if named_source.exists():
                named_target = target_dir / "qr_named.png"
                shutil.copy2(named_source, named_target)
            else:
                logging.warning(
                    "qr_named.png not found for clinic_id=%s",
                    record.clinic_id,
                )
        else:
            logging.warning(
                "Missing qr_named_path for clinic_id=%s",
                record.clinic_id,
            )

        info_path = target_dir / "info.txt"
        info_path.write_text(
            _render_info(cfg, record, now),
            encoding="utf-8",
        )

        results.append(
            DeliveryResult(
                output_dir=target_dir,
                clinic_id=record.clinic_id,
                clinic_name=record.clinic_name,
            )
        )

    return results


def create_delivery_from_mapping_csv(
    cfg: AppConfig,
    mapping_csv_path: str | Path,
    delivery_root: str | Path | None = None,
) -> list[DeliveryResult]:
    records = _load_mapping_csv(mapping_csv_path)
    return create_delivery_packages(cfg, records, delivery_root=delivery_root)


def _load_mapping_csv(path: str | Path) -> list[MappingRecord]:
    csv_path = Path(path)
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        records: list[MappingRecord] = []
        for row in reader:
            records.append(
                MappingRecord(
                    clinic_name=row.get("clinic_name", ""),
                    clinic_id=row.get("clinic_id", ""),
                    status=row.get("status", ""),
                    address=row.get("address", ""),
                    phone=row.get("phone", ""),
                    director=row.get("director", ""),
                    homepage=row.get("homepage", ""),
                    url=row.get("url", ""),
                    page_path=row.get("page_path", ""),
                    qr_path=row.get("qr_path", ""),
                    qr_named_path=row.get("qr_named_path", ""),
                )
            )
        return records


def _render_info(cfg: AppConfig, record: MappingRecord, created_at: str) -> str:
    return (
        f"치과명: {record.clinic_name}\n"
        f"식별코드: {record.clinic_id}\n"
        f"URL: {record.url}\n"
        f"주소: {_display_or_dash(record.address)}\n"
        f"전화: {_display_or_dash(record.phone)}\n"
        f"대표원장: {_display_or_dash(record.director)}\n"
        f"홈페이지: {_display_or_dash(record.homepage)}\n"
        f"안내: {cfg.message_active}\n"
        f"생성일: {created_at}\n"
    )


def _is_active(status: str) -> bool:
    return str(status).upper() == "ACTIVE"


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _display_or_dash(value: str) -> str:
    return value if value else "-"
