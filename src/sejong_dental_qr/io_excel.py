"""Excel I/O helpers for clinic names."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import pandas as pd

from .normalize import normalize_name


def read_clinic_names(
    input_excel_path: str,
    sheet_index: int,
    name_column: str,
) -> list[str]:
    df = pd.read_excel(
        input_excel_path,
        sheet_name=sheet_index,
        engine="openpyxl",
    )

    if name_column not in df.columns:
        raise ValueError(f"Missing required column: {name_column}")

    raw_values = df[name_column].tolist()
    normalized: list[str] = []
    empty_count = 0

    for value in raw_values:
        if _is_nan(value):
            empty_count += 1
            continue

        if not isinstance(value, str):
            value = str(value)

        name = normalize_name(value)
        if not name:
            empty_count += 1
            continue

        normalized.append(name)

    if empty_count:
        logging.warning(
            "Removed %s empty clinic name(s) after normalization.",
            empty_count,
        )

    duplicates = _find_duplicates(normalized)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate clinic names after normalization: {joined}")

    return normalized


def _is_nan(value: Any) -> bool:
    try:
        return pd.isna(value)
    except TypeError:
        return False


def _find_duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {name for name, count in counts.items() if count > 1}
