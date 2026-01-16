"""
엑셀(clinics.xlsx) 입력 처리 모듈.

- 무엇(What): 치과명/주소/전화/대표원장/홈페이지 컬럼을 읽어 ClinicInput으로 변환한다.
- 왜(Why): 입력 데이터 품질(중복/누락)을 조기에 검증하여 운영 오류를 방지한다.
- 어떻게(How): 치과명 정규화(normalize) + 중복 체크 + 필수 컬럼 검증(fail-fast).

주의: 치과명은 clinic_id의 동일성 키로 사용되므로, 오타/변경은 신규 치과로 인식될 수 있다.
"""

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


# -----------------------------------------------------------------------------
# [WHY] 운영자가 관리하는 엑셀을 신뢰 가능한 레코드로 변환해야 한다.
# [WHAT] 필수 컬럼 검증 + 치과명 정규화 + 중복 검증 후 ClinicInput 리스트 반환.
# [HOW] pandas.read_excel(openpyxl) → normalize_name → fail-fast.
# -----------------------------------------------------------------------------
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

    # WARNING: 치과명 중복은 clinic_id 혼선을 야기하므로 즉시 실패한다.
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
