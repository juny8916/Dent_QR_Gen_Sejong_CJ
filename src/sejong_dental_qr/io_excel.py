"""Excel I/O helpers for clinic records."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .normalize import normalize_name


@dataclass(frozen=True)
class ClinicInput:
    name: str
    address: str
    phone: str
    director: str
    homepage: str


def read_clinic_records(
    input_excel_path: str,
    sheet_index: int,
    name_column: str,
    address_column: str,
    phone_column: str,
    director_column: str,
    homepage_column: str,
) -> list[ClinicInput]:
    df = pd.read_excel(
        input_excel_path,
        sheet_name=sheet_index,
        engine="openpyxl",
    )

    required_columns = [
        name_column,
        address_column,
        phone_column,
        director_column,
        homepage_column,
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Missing required column(s): {joined}")

    records: list[ClinicInput] = []
    empty_count = 0

    for _, row in df.iterrows():
        raw_name = row[name_column]
        if _is_nan(raw_name):
            empty_count += 1
            continue

        if not isinstance(raw_name, str):
            raw_name = str(raw_name)

        name = normalize_name(raw_name)
        if not name:
            empty_count += 1
            continue

        address = _clean_text(row[address_column])
        phone = _clean_text(row[phone_column])
        director = _clean_text(row[director_column])
        homepage = _clean_text(row[homepage_column])

        _warn_missing_field(name, "주소", address)
        _warn_missing_field(name, "전화", phone)
        _warn_missing_field(name, "대표원장", director)
        _warn_missing_field(name, "홈페이지", homepage)

        records.append(
            ClinicInput(
                name=name,
                address=address,
                phone=phone,
                director=director,
                homepage=homepage,
            )
        )

    if empty_count:
        logging.warning(
            "Removed %s empty clinic name(s) after normalization.",
            empty_count,
        )

    names = [record.name for record in records]
    duplicates = _find_duplicates(names)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate clinic names after normalization: {joined}")

    return records


def _is_nan(value: Any) -> bool:
    try:
        return pd.isna(value)
    except TypeError:
        return False


def _clean_text(value: Any) -> str:
    if _is_nan(value) or value is None:
        return ""
    return str(value).strip()


def _warn_missing_field(clinic_name: str, field_label: str, value: str) -> None:
    if not value:
        logging.warning("Missing %s for clinic_name=%s", field_label, clinic_name)


def _find_duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {name for name, count in counts.items() if count > 1}
