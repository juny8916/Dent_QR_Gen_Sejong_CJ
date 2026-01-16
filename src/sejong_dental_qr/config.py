"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Mapping


DEFAULT_MESSAGE_ACTIVE = "해당 치과는 2026년도 세종시 치과의사협회 가입 치과입니다"
DEFAULT_MESSAGE_INACTIVE = "현재 2026 가입 치과 목록에 없습니다. 협회에 문의하세요."
_MISSING = object()


@dataclass(frozen=True)
class AppConfig:
    year: int
    base_url: str
    input_excel_path: str
    clinics_source: str = "local"
    clinics_xlsx_url: str = ""
    clinics_hash_path: str = "data/clinics.sha256"
    sheet_index: int = 0
    name_column: str = "치과명"
    address_column: str = "주소"
    phone_column: str = "전화"
    director_column: str = "대표원장"
    homepage_column: str = "홈페이지"
    id_map_path: str = "data/id_map.csv"
    site_root: str = "docs"
    path_prefix: str = "c"
    output_root: str = "output"
    message_active: str = DEFAULT_MESSAGE_ACTIVE
    message_inactive: str = DEFAULT_MESSAGE_INACTIVE
    noindex: bool = True
    analytics_provider: str = "none"
    ga4_measurement_id: str = ""
    qr_error_correction: str = "H"
    qr_box_size: int = 10
    qr_border: int = 4
    generate_qr_named: bool = True
    caption_font_path: str = ""
    caption_font_size: int = 28
    generate_delivery: bool = True
    generate_outbox: bool = True
    outbox_mode: str = "changed"
    outbox_root: str = "output/outbox"

    def validate(self, allow_missing_base_url: bool = False) -> None:
        errors: list[str] = []

        if not _is_int(self.year) or self.year <= 0:
            errors.append("year must be a positive integer")

        if not _is_nonempty_str(self.input_excel_path):
            errors.append("input_excel_path must be a non-empty string")

        if not _is_nonempty_str(self.clinics_source):
            errors.append("clinics_source must be a non-empty string")
        elif self.clinics_source not in {"local", "url"}:
            errors.append("clinics_source must be 'local' or 'url'")

        if not isinstance(self.clinics_xlsx_url, str):
            errors.append("clinics_xlsx_url must be a string")
        elif self.clinics_source == "url" and not self.clinics_xlsx_url.strip():
            errors.append("clinics_xlsx_url is required when clinics_source is 'url'")

        if not _is_nonempty_str(self.clinics_hash_path):
            errors.append("clinics_hash_path must be a non-empty string")

        if not _is_int(self.sheet_index) or self.sheet_index < 0:
            errors.append("sheet_index must be a non-negative integer")

        if not _is_nonempty_str(self.name_column):
            errors.append("name_column must be a non-empty string")

        if not _is_nonempty_str(self.address_column):
            errors.append("address_column must be a non-empty string")

        if not _is_nonempty_str(self.phone_column):
            errors.append("phone_column must be a non-empty string")

        if not _is_nonempty_str(self.director_column):
            errors.append("director_column must be a non-empty string")

        if not _is_nonempty_str(self.homepage_column):
            errors.append("homepage_column must be a non-empty string")

        if not _is_nonempty_str(self.id_map_path):
            errors.append("id_map_path must be a non-empty string")

        if not _is_nonempty_str(self.site_root):
            errors.append("site_root must be a non-empty string")

        if not _is_nonempty_str(self.path_prefix):
            errors.append("path_prefix must be a non-empty string")

        if not _is_nonempty_str(self.output_root):
            errors.append("output_root must be a non-empty string")

        if not _is_nonempty_str(self.message_active):
            errors.append("message_active must be a non-empty string")

        if not _is_nonempty_str(self.message_inactive):
            errors.append("message_inactive must be a non-empty string")

        if not isinstance(self.noindex, bool):
            errors.append("noindex must be a boolean")

        if not _is_nonempty_str(self.analytics_provider):
            errors.append("analytics_provider must be a non-empty string")
        elif self.analytics_provider not in {"none", "ga4"}:
            errors.append("analytics_provider must be 'none' or 'ga4'")

        if not isinstance(self.ga4_measurement_id, str):
            errors.append("ga4_measurement_id must be a string")
        elif self.analytics_provider == "ga4" and not self.ga4_measurement_id.strip():
            errors.append("ga4_measurement_id is required when analytics_provider is 'ga4'")

        if not isinstance(self.generate_delivery, bool):
            errors.append("generate_delivery must be a boolean")

        if not isinstance(self.generate_qr_named, bool):
            errors.append("generate_qr_named must be a boolean")

        if not isinstance(self.generate_outbox, bool):
            errors.append("generate_outbox must be a boolean")

        if not isinstance(self.caption_font_path, str):
            errors.append("caption_font_path must be a string")

        if not _is_int(self.caption_font_size) or self.caption_font_size <= 0:
            errors.append("caption_font_size must be a positive integer")

        if not _is_nonempty_str(self.outbox_mode):
            errors.append("outbox_mode must be a non-empty string")
        elif self.outbox_mode != "changed":
            errors.append("outbox_mode must be 'changed'")

        if not _is_nonempty_str(self.outbox_root):
            errors.append("outbox_root must be a non-empty string")

        if not _is_nonempty_str(self.qr_error_correction):
            errors.append("qr_error_correction must be a non-empty string")
        elif self.qr_error_correction not in {"L", "M", "Q", "H"}:
            errors.append("qr_error_correction must be one of L, M, Q, H")

        if not _is_int(self.qr_box_size) or self.qr_box_size <= 0:
            errors.append("qr_box_size must be a positive integer")

        if not _is_int(self.qr_border) or self.qr_border < 0:
            errors.append("qr_border must be a non-negative integer")

        if not _is_nonempty_str(self.base_url) and not allow_missing_base_url:
            errors.append("base_url is required unless allow_missing_base_url is true")

        if errors:
            raise ValueError("Invalid config:\n- " + "\n- ".join(errors))


def load_config(path: str | Path, allow_missing_base_url: bool = False) -> AppConfig:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    if not isinstance(data, Mapping):
        raise ValueError("Config must be a TOML table at the top level")

    config = AppConfig(
        year=_read_int(data, "year"),
        base_url=_read_str(data, "base_url", ""),
        input_excel_path=_read_str(data, "input_excel_path"),
        clinics_source=_read_str(data, "clinics_source", "local"),
        clinics_xlsx_url=_read_str(data, "clinics_xlsx_url", ""),
        clinics_hash_path=_read_str(data, "clinics_hash_path", "data/clinics.sha256"),
        sheet_index=_read_int(data, "sheet_index", 0),
        name_column=_read_str(data, "name_column", "치과명"),
        address_column=_read_str(data, "address_column", "주소"),
        phone_column=_read_str(data, "phone_column", "전화"),
        director_column=_read_str(data, "director_column", "대표원장"),
        homepage_column=_read_str(data, "homepage_column", "홈페이지"),
        id_map_path=_read_str(data, "id_map_path", "data/id_map.csv"),
        site_root=_read_str(data, "site_root", "docs"),
        path_prefix=_read_str(data, "path_prefix", "c"),
        output_root=_read_str(data, "output_root", "output"),
        message_active=_read_str(data, "message_active", DEFAULT_MESSAGE_ACTIVE),
        message_inactive=_read_str(data, "message_inactive", DEFAULT_MESSAGE_INACTIVE),
        noindex=_read_bool(data, "noindex", True),
        analytics_provider=_read_str(data, "analytics_provider", "none"),
        ga4_measurement_id=_read_str(data, "ga4_measurement_id", ""),
        qr_error_correction=_read_str(data, "qr_error_correction", "H"),
        qr_box_size=_read_int(data, "qr_box_size", 10),
        qr_border=_read_int(data, "qr_border", 4),
        generate_delivery=_read_bool(data, "generate_delivery", True),
        generate_qr_named=_read_bool(data, "generate_qr_named", True),
        caption_font_path=_read_str(data, "caption_font_path", ""),
        caption_font_size=_read_int(data, "caption_font_size", 28),
        generate_outbox=_read_bool(data, "generate_outbox", True),
        outbox_mode=_read_str(data, "outbox_mode", "changed"),
        outbox_root=_read_str(data, "outbox_root", "output/outbox"),
    )
    config.validate(allow_missing_base_url=allow_missing_base_url)
    return config


def _read_str(data: Mapping[str, Any], key: str, default: object = _MISSING) -> str:
    value = data.get(key, _MISSING)
    if value is _MISSING:
        if default is _MISSING:
            raise ValueError(f"Missing required config value: {key}")
        return default  # type: ignore[return-value]
    if not isinstance(value, str):
        raise ValueError(f"Config value '{key}' must be a string")
    return value


def _read_int(data: Mapping[str, Any], key: str, default: object = _MISSING) -> int:
    value = data.get(key, _MISSING)
    if value is _MISSING:
        if default is _MISSING:
            raise ValueError(f"Missing required config value: {key}")
        return default  # type: ignore[return-value]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Config value '{key}' must be an integer")
    return value


def _read_bool(data: Mapping[str, Any], key: str, default: object = _MISSING) -> bool:
    value = data.get(key, _MISSING)
    if value is _MISSING:
        if default is _MISSING:
            raise ValueError(f"Missing required config value: {key}")
        return default  # type: ignore[return-value]
    if not isinstance(value, bool):
        raise ValueError(f"Config value '{key}' must be a boolean")
    return value


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
