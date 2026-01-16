"""
id_map.csv(치과명 ↔ clinic_id) 영속 저장소(persistent mapping) 처리 모듈.

- 무엇(What): 치과명 기준으로 clinic_id를 유지/신규 발급하고 상태(ACTIVE/INACTIVE)를 갱신한다.
- 왜(Why): QR은 clinic_id 기반이므로, 동일 치과는 영구히 같은 ID를 유지해야 한다.
- 어떻게(How): 기존 id_map 로드 → 치과명 매칭 → 신규 ID 발급 → 상태/메타데이터 업데이트.

주의: 치과명은 동일성 키이므로, 치과명 변경/오타는 신규 치과로 인식될 수 있다.
개인정보(환자 데이터)는 저장/처리하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable

import pandas as pd

from .io_excel import ClinicInput


# id_map.csv 필수 컬럼(정책상 고정). 순서가 변하면 외부 운영 스크립트에 영향 가능.
CORE_COLUMNS = [
    "clinic_id",
    "clinic_name",
    "status",
    "first_seen_at",
    "last_seen_at",
]

# 추가 메타데이터 컬럼(치과 기본 정보 유지용).
EXTRA_COLUMNS = [
    "address",
    "phone",
    "director",
    "homepage",
]

COLUMNS = CORE_COLUMNS + EXTRA_COLUMNS


@dataclass(frozen=True)
class IdMapResult:
    data: pd.DataFrame
    new_ids: list[str]


def load_id_map(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame(columns=COLUMNS)

    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    missing_core = [col for col in CORE_COLUMNS if col not in df.columns]
    if missing_core:
        raise ValueError(f"id_map is missing required columns: {', '.join(missing_core)}")
    for col in EXTRA_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS].copy()


def save_id_map(df: pd.DataFrame, path: str | Path) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")


# -----------------------------------------------------------------------------
# [WHY] clinic_id 영구 고정 정책을 유지하면서 최신 ACTIVE/INACTIVE 상태를 반영한다.
# [WHAT] 입력 레코드(ClinicInput)와 기존 id_map을 합쳐 새 DataFrame을 생성한다.
# [HOW] 치과명 기준 매칭 + 신규 ID 발급 + last_seen_at 갱신 + 빈 값은 기존 값 유지.
# -----------------------------------------------------------------------------
def update_id_map(
    clinic_records: Iterable[ClinicInput],
    year: int,
    existing_df: pd.DataFrame,
) -> IdMapResult:
    records = list(clinic_records)
    names = [record.name for record in records]
    # WARNING: 치과명 중복은 clinic_id 충돌을 유발하므로 즉시 실패한다.
    if len(names) != len(set(names)):
        raise ValueError("Duplicate clinic names provided to update_id_map")

    _ensure_columns(existing_df)
    _check_duplicate_names(existing_df)

    active_names = set(names)
    record_by_name = {record.name: record for record in records}
    prefix = f"SJ{year % 100:02d}-"
    max_number = _max_existing_number(existing_df["clinic_id"], prefix)
    now = _now_iso()

    updated_rows: list[dict[str, str]] = []
    for _, row in existing_df.iterrows():
        name = _safe_str(row["clinic_name"])
        record = record_by_name.get(name)
        # 이번 입력에 있으면 ACTIVE, 없으면 INACTIVE (정회원 판정 기준)
        status = "ACTIVE" if record else "INACTIVE"
        last_seen_at = now if status == "ACTIVE" else _safe_str(row["last_seen_at"])
        # 빈 값은 운영 실수 방지를 위해 기존 값을 유지한다.
        address = _merge_field(record.address if record else "", row.get("address", ""))
        phone = _merge_field(record.phone if record else "", row.get("phone", ""))
        director = _merge_field(record.director if record else "", row.get("director", ""))
        homepage = _merge_field(record.homepage if record else "", row.get("homepage", ""))
        updated_rows.append(
            {
                "clinic_id": _safe_str(row["clinic_id"]),
                "clinic_name": name,
                "status": status,
                "first_seen_at": _safe_str(row["first_seen_at"]),
                "last_seen_at": last_seen_at,
                "address": address,
                "phone": phone,
                "director": director,
                "homepage": homepage,
            }
        )

    existing_names = set(existing_df["clinic_name"])
    # 신규 치과는 prefix 규칙(SJYY-####)으로 ID 발급.
    new_names = sorted(active_names - existing_names)
    new_ids: list[str] = []
    for name in new_names:
        record = record_by_name[name]
        max_number += 1
        clinic_id = f"{prefix}{max_number:04d}"
        new_ids.append(clinic_id)
        updated_rows.append(
            {
                "clinic_id": clinic_id,
                "clinic_name": name,
                "status": "ACTIVE",
                "first_seen_at": now,
                "last_seen_at": now,
                "address": record.address,
                "phone": record.phone,
                "director": record.director,
                "homepage": record.homepage,
            }
        )

    updated_df = pd.DataFrame(updated_rows, columns=COLUMNS)
    return IdMapResult(data=updated_df, new_ids=new_ids)


def _ensure_columns(df: pd.DataFrame) -> None:
    missing_core = [col for col in CORE_COLUMNS if col not in df.columns]
    if missing_core:
        raise ValueError(f"id_map is missing required columns: {', '.join(missing_core)}")
    for col in EXTRA_COLUMNS:
        if col not in df.columns:
            df[col] = ""


def _check_duplicate_names(df: pd.DataFrame) -> None:
    if df["clinic_name"].duplicated().any():
        duplicates = sorted(df.loc[df["clinic_name"].duplicated(), "clinic_name"].unique())
        joined = ", ".join(duplicates)
        raise ValueError(f"id_map has duplicate clinic names: {joined}")


def _max_existing_number(clinic_ids: Iterable[str], prefix: str) -> int:
    max_number = 0
    pattern = re.compile(re.escape(prefix) + r"(\d+)$")
    for clinic_id in clinic_ids:
        if not isinstance(clinic_id, str):
            continue
        match = pattern.match(clinic_id.strip())
        if not match:
            continue
        try:
            number = int(match.group(1))
        except ValueError:
            continue
        max_number = max(max_number, number)
    return max_number


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _safe_str(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _merge_field(new_value: str, old_value: object) -> str:
    if new_value:
        return new_value
    return _safe_str(old_value)
