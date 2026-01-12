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
    address: str,
    phone: str,
    director: str,
    homepage: str,
    build_timestamp: str,
) -> str:
    status_upper = str(status).upper()
    is_active = status_upper == "ACTIVE"
    message = cfg.message_active if is_active else cfg.message_inactive
    badge_text = (
        f"✅ {cfg.year} 협회 가입 치과 (ACTIVE)"
        if is_active
        else "⚠️ 현재 가입 목록에 없음 (INACTIVE)"
    )
    validity = f"{cfg.year}-01-01 ~ {cfg.year}-12-31"

    safe_name = html.escape(clinic_name)
    safe_message = html.escape(message)
    safe_badge = html.escape(badge_text)
    safe_validity = html.escape(validity)
    safe_updated = html.escape(build_timestamp)
    safe_id = html.escape(clinic_id)

    address_html = html.escape(_display_or_dash(address))
    phone_html = html.escape(_display_or_dash(phone))
    director_html = html.escape(_display_or_dash(director))
    homepage_html = _render_homepage(homepage)

    body = (
        f"<div class=\"badge {'active' if is_active else 'inactive'}\">{safe_badge}</div>"
        f"<h1>{safe_name}</h1>"
        f"<p class=\"message\">{safe_message}</p>"
        "<div class=\"card\">"
        "<div class=\"info-row\"><span class=\"label\">📍 주소</span>"
        f"<span class=\"value\">{address_html}</span></div>"
        "<div class=\"info-row\"><span class=\"label\">☎ 전화</span>"
        f"<span class=\"value\">{phone_html}</span></div>"
        "<div class=\"info-row\"><span class=\"label\">👨‍⚕️ 대표원장</span>"
        f"<span class=\"value\">{director_html}</span></div>"
        "<div class=\"info-row\"><span class=\"label\">🌐 홈페이지</span>"
        f"<span class=\"value\">{homepage_html}</span></div>"
        "</div>"
        "<div class=\"meta\">"
        f"<div>유효기간: {safe_validity}</div>"
        f"<div>최종 업데이트: {safe_updated}</div>"
        f"<div>확인 코드: {safe_id}</div>"
        "</div>"
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
        "h1{font-size:1.7rem;margin:0 0 10px;}"
        "p{margin:0 0 12px;}"
        ".badge{display:inline-block;padding:6px 10px;border-radius:999px;"
        "font-size:0.95rem;font-weight:700;margin:0 0 12px;}"
        ".badge.active{background:#e6f4ea;color:#1e7f3d;}"
        ".badge.inactive{background:#fff4e5;color:#9a5a00;}"
        ".message{font-size:1.1rem;font-weight:700;margin-bottom:14px;}"
        ".card{background:#fff;border-radius:14px;padding:14px 16px;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.06);}"
        ".info-row{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #eee;}"
        ".info-row:last-child{border-bottom:none;}"
        ".label{min-width:110px;color:#444;font-weight:600;}"
        ".value{color:#111;word-break:break-word;}"
        ".meta{color:#555;font-size:0.95rem;margin-top:14px;}"
        ".meta div{margin-bottom:6px;}"
        "@media (min-width:768px){"
        "h1{font-size:2rem;}"
        ".wrap{padding:40px 24px;}"
        ".label{min-width:140px;}"
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


def _display_or_dash(value: str) -> str:
    return value.strip() if value and value.strip() else "-"


def _render_homepage(value: str) -> str:
    raw = value.strip() if value else ""
    if not raw:
        return "-"

    if raw.startswith(("http://", "https://")):
        link = raw
        display = raw
    elif "://" in raw:
        return html.escape(raw)
    else:
        link = f"https://{raw}"
        display = link

    safe_link = html.escape(link, quote=True)
    safe_display = html.escape(display)
    return f"<a href=\"{safe_link}\" rel=\"noopener\">{safe_display}</a>"
