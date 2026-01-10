"""Change planning between id_map snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class ChangeRecord:
    clinic_id: str
    clinic_name: str
    change_type: str


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
