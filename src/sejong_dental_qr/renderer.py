"""HTML rendering helpers for static pages."""

from __future__ import annotations

import html

from .config import AppConfig


def render_root_index(cfg: AppConfig) -> str:
    body = (
        "<h1>QR 전용 안내(목록 없음)</h1>"
        "<p>이 페이지는 치과별 QR 코드 전용 안내 페이지입니다.</p>"
    )
    return _render_page(cfg, title="QR 안내", body=body)


def render_404(cfg: AppConfig) -> str:
    body = "<h1>유효하지 않은 코드</h1><p>요청하신 페이지를 찾을 수 없습니다.</p>"
    return _render_page(cfg, title="유효하지 않은 코드", body=body)


def render_clinic_page(
    cfg: AppConfig,
    clinic_id: str,
    clinic_name: str,
    status: str,
) -> str:
    safe_name = html.escape(clinic_name)
    safe_id = html.escape(clinic_id)
    status_upper = str(status).upper()
    message = cfg.message_active if status_upper == "ACTIVE" else cfg.message_inactive
    safe_message = html.escape(message)

    body = (
        f"<h1>{safe_name}</h1>"
        f"<p class=\"meta\">코드: {safe_id}</p>"
        f"<p class=\"message\">{safe_message}</p>"
    )
    return _render_page(cfg, title=safe_name, body=body)


def _render_page(cfg: AppConfig, title: str, body: str) -> str:
    safe_title = html.escape(title)
    robots = _render_robots(cfg.noindex)
    return (
        "<!doctype html>"
        "<html lang=\"ko\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"{robots}"
        f"<title>{safe_title}</title>"
        "<style>"
        ":root{color-scheme:light;}"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "line-height:1.6;margin:0;background:#f7f7f7;color:#1a1a1a;}"
        ".wrap{max-width:720px;margin:0 auto;padding:24px 18px;}"
        "h1{font-size:1.6rem;margin:0 0 12px;}"
        "p{margin:0 0 12px;}"
        ".meta{color:#555;font-size:0.95rem;}"
        ".message{font-size:1.1rem;font-weight:600;}"
        "@media (min-width:768px){"
        "h1{font-size:2rem;}"
        ".wrap{padding:40px 24px;}"
        "}"
        "</style>"
        "</head>"
        "<body>"
        "<main class=\"wrap\">"
        f"{body}"
        "</main>"
        "</body>"
        "</html>"
    )


def _render_robots(noindex: bool) -> str:
    if not noindex:
        return ""
    return "<meta name=\"robots\" content=\"noindex,nofollow\">"
