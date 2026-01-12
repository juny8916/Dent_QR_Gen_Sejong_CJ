"""CLI entry points for build/preview commands."""

from __future__ import annotations

import argparse
import functools
import http.server
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import load_config
from .delivery import create_delivery_packages
from .id_map import load_id_map, save_id_map, update_id_map
from .io_excel import read_clinic_records
from .outbox import create_outbox, OutboxResult
from .planner import build_changes
from .qrgen import make_qr_named_png, make_qr_png
from .renderer import render_404, render_clinic_page, render_root_index
from .report import MappingRecord, write_changes_csv, write_mapping_csv


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sejong_dental_qr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Generate QR assets and static pages")
    build.add_argument("--config", required=True, help="Path to config.toml")
    build.add_argument("--skip-qr", action="store_true", help="Skip QR PNG generation")

    preview = subparsers.add_parser("preview", help="Serve docs/ for preview")
    preview.add_argument("--port", type=int, default=8000, help="Port to bind")

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        if args.command == "build":
            return _run_build(args)
        if args.command == "preview":
            return _run_preview(args)
    except Exception as exc:  # noqa: BLE001
        logging.error("%s", exc)
        return 1

    parser.error("Unknown command")
    return 2


def _run_build(args: argparse.Namespace) -> int:
    cfg = load_config(args.config, allow_missing_base_url=args.skip_qr)

    clinic_records = read_clinic_records(
        cfg.input_excel_path,
        cfg.sheet_index,
        cfg.name_column,
        cfg.address_column,
        cfg.phone_column,
        cfg.director_column,
        cfg.homepage_column,
    )
    logging.info("Loaded %s clinic record(s) from Excel.", len(clinic_records))

    df_prev = load_id_map(cfg.id_map_path)
    id_map_result = update_id_map(clinic_records, cfg.year, df_prev)
    df_next = id_map_result.data
    save_id_map(df_next, cfg.id_map_path)

    changes = build_changes(df_prev, df_next)

    site_root = Path(cfg.site_root)
    _write_text(site_root / "index.html", render_root_index(cfg))
    _write_text(site_root / "404.html", render_404(cfg))

    base_url = cfg.base_url.strip()
    url_prefix = _build_url_prefix(base_url, cfg.path_prefix) if base_url else ""
    qr_root = Path(cfg.output_root) / "qr"
    build_timestamp = _now_iso()

    mapping_records: list[MappingRecord] = []
    active_count = 0
    inactive_count = 0

    for _, row in df_next.iterrows():
        clinic_id = str(row["clinic_id"])
        clinic_name = str(row["clinic_name"])
        status = str(row["status"]).upper()
        address = _safe_str(row.get("address", ""))
        phone = _safe_str(row.get("phone", ""))
        director = _safe_str(row.get("director", ""))
        homepage = _safe_str(row.get("homepage", ""))

        page_path = site_root / cfg.path_prefix / clinic_id / "index.html"
        _write_text(
            page_path,
            render_clinic_page(
                cfg,
                clinic_id,
                clinic_name,
                status,
                address,
                phone,
                director,
                homepage,
                build_timestamp,
            ),
        )

        url = f"{url_prefix}{clinic_id}/" if url_prefix else ""

        qr_path = ""
        qr_named_path = ""
        if status == "ACTIVE":
            active_count += 1
            if not args.skip_qr:
                qr_path = str(qr_root / f"{clinic_id}.png")
                make_qr_png(
                    url,
                    qr_path,
                    cfg.qr_error_correction,
                    cfg.qr_box_size,
                    cfg.qr_border,
                )
                if cfg.generate_qr_named:
                    qr_named_path = str(qr_root / f"{clinic_id}_named.png")
                    font_path = cfg.caption_font_path.strip() or None
                    make_qr_named_png(
                        Path(qr_path),
                        clinic_name,
                        Path(qr_named_path),
                        font_path,
                        cfg.caption_font_size,
                    )
        else:
            inactive_count += 1

        mapping_records.append(
            MappingRecord(
                clinic_name=clinic_name,
                clinic_id=clinic_id,
                status=status,
                address=address,
                phone=phone,
                director=director,
                homepage=homepage,
                url=url,
                page_path=str(page_path),
                qr_path=qr_path,
                qr_named_path=qr_named_path,
            )
        )

    output_root = Path(cfg.output_root)
    write_mapping_csv(mapping_records, output_root / "mapping.csv")
    write_changes_csv(changes, output_root / "changes.csv")

    if cfg.generate_delivery:
        if args.skip_qr:
            logging.warning("Delivery skipped because --skip-qr was set.")
        else:
            create_delivery_packages(cfg, mapping_records)

    outbox_result: OutboxResult | None = None
    if cfg.generate_outbox:
        if args.skip_qr:
            logging.warning("Outbox skipped because --skip-qr was set.")
        else:
            outbox_result = create_outbox(cfg, mapping_records, changes)

    _log_summary(len(clinic_records), active_count, inactive_count, changes, outbox_result)
    return 0


def _run_preview(args: argparse.Namespace) -> int:
    site_root = Path("docs")
    if not site_root.exists():
        raise FileNotFoundError(f"Site root not found: {site_root}")

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(site_root),
    )
    server = http.server.ThreadingHTTPServer(("", args.port), handler)
    logging.info("Serving %s at http://localhost:%s", site_root, args.port)
    server.serve_forever()
    return 0


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_url_prefix(base_url: str, path_prefix: str) -> str:
    return f"{base_url.rstrip('/')}/{path_prefix.strip('/')}/"


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _safe_str(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _log_summary(
    total: int,
    active: int,
    inactive: int,
    changes: list,
    outbox_result: OutboxResult | None,
) -> None:
    counts = {"NEW": 0, "DEACTIVATED": 0, "REACTIVATED": 0, "UNCHANGED": 0}
    for change in changes:
        counts[change.change_type] = counts.get(change.change_type, 0) + 1

    logging.info("Summary: total=%s active=%s inactive=%s", total, active, inactive)
    logging.info(
        "Changes: NEW=%s DEACTIVATED=%s REACTIVATED=%s UNCHANGED=%s",
        counts["NEW"],
        counts["DEACTIVATED"],
        counts["REACTIVATED"],
        counts["UNCHANGED"],
    )
    if outbox_result:
        logging.info(
            "Outbox: targets=%s zips=%s",
            outbox_result.targets,
            outbox_result.zips_created,
        )
