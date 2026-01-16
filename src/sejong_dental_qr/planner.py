"""
id_map 스냅샷 간 변경사항(change) 계산 모듈.

- 무엇(What): 이전/현재 id_map을 비교해 NEW/DEACTIVATED/REACTIVATED/UNCHANGED를 산출한다.
- 왜(Why): outbox 대상(NEW/REACTIVATED)을 선별하고 운영 리포트를 만들기 위함.
- 어떻게(How): clinic_id 기준으로 상태 전환을 비교한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class ChangeRecord:
    clinic_id: str
    clinic_name: str
    change_type: str


# -----------------------------------------------------------------------------
# [WHY] 변경 유형을 명확히 구분해 운영 전달(outbox) 대상만 선별한다.
# [WHAT] clinic_id 기준으로 상태 전환을 비교해 ChangeRecord 리스트를 만든다.
# [HOW] prev/next lookup 생성 후 ACTIVE/INACTIVE 전환 규칙으로 분류한다.
# -----------------------------------------------------------------------------
def build_changes(df_prev: pd.DataFrame, df_next: pd.DataFrame) -> list[ChangeRecord]:
    prev_lookup = _to_lookup(df_prev)
    next_lookup = _to_lookup(df_next)

    changes: list[ChangeRecord] = []
    for clinic_id, next_row in next_lookup.items():
        prev_row = prev_lookup.get(clinic_id)
        if prev_row is None:
            change_type = "NEW"
        else:
            prev_status = prev_row["status"]
            next_status = next_row["status"]
            if prev_status == "ACTIVE" and next_status == "INACTIVE":
                change_type = "DEACTIVATED"
            elif prev_status == "INACTIVE" and next_status == "ACTIVE":
                change_type = "REACTIVATED"
            else:
                change_type = "UNCHANGED"

        changes.append(
            ChangeRecord(
                clinic_id=clinic_id,
                clinic_name=next_row["clinic_name"],
                change_type=change_type,
            )
        )

    return changes


def _to_lookup(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        clinic_id = str(row.get("clinic_id", "")).strip()
        if not clinic_id:
            continue
        lookup[clinic_id] = {
            "clinic_name": str(row.get("clinic_name", "")).strip(),
            "status": str(row.get("status", "")).strip(),
        }
    return lookup
