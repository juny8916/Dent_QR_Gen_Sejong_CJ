"""HTML rendering helpers for static pages."""

from __future__ import annotations

import html
from urllib.parse import urlparse

from .config import AppConfig


def render_root_index(cfg: AppConfig) -> str:
    body = (
        "<div class=\"card\">"
        "<h1>QR 전용 안내(목록 없음)</h1>"
        "<p>이 페이지는 치과별 QR 코드 전용 안내 페이지입니다.</p>"
        "</div>"
    )
    return _render_page(cfg, title="QR 안내", body=body)


def render_404(cfg: AppConfig) -> str:
    body = (
        "<div class=\"card\">"
        "<h1>유효하지 않은 코드</h1>"
        "<p>요청하신 페이지를 찾을 수 없습니다.</p>"
        "</div>"
    )
    return _render_page(cfg, title="유효하지 않은 코드", body=body)


def render_outbox_index(cfg: AppConfig, build_timestamp: str, zip_names: list[str]) -> str:
    items = "".join(
        f"<li><a href=\"zips/{html.escape(name, quote=True)}\">{html.escape(name)}</a></li>"
        for name in zip_names
    )
    if not items:
        items = "<li>대상 없음</li>"

    body = (
        "<h1>Outbox 다운로드</h1>"
        f"<p class=\"meta\">최종 업데이트: {html.escape(build_timestamp)}</p>"
        "<p><a href=\"sendlist.csv\">sendlist.csv 다운로드</a></p>"
        f"<ul class=\"zip-list\">{items}</ul>"
    )
    return _render_page(cfg, title="Outbox 다운로드", body=body)


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
    badge_text = "정회원" if is_active else "비회원(확인되지 않음)"
    validity = f"{cfg.year}-01-01 ~ {cfg.year}-12-31"

    josa = _choose_josa(clinic_name)
    member_line = (
        f"({clinic_name}){josa} {cfg.year} '세종특별자치시 치과의사회' 정회원 입니다."
    )
    sub_line = "세종시 치과의사회는 시민의 구강건강을 지키는 공식 치과의사 단체입니다."
    warning_line = "현재 정회원으로 확인되지 않습니다."

    safe_name = html.escape(clinic_name)
    safe_badge = html.escape(badge_text)
    safe_validity = html.escape(validity)
    safe_updated = html.escape(build_timestamp)
    safe_id = html.escape(clinic_id)

    safe_member_line = html.escape(member_line)
    safe_sub_line = html.escape(sub_line)
    safe_warning_line = html.escape(warning_line)
    safe_inactive_message = html.escape(cfg.message_inactive)

    address_html = html.escape(_display_or_dash(address))
    director_html = html.escape(_display_or_dash(director))

    phone_html = html.escape(_display_or_dash(phone))
    homepage_html = _render_homepage(homepage)

    asset_base = _asset_base(cfg)
    kda_logo = html.escape(f"{asset_base}assets/logos/kda.svg", quote=True)
    sejong_logo = html.escape(f"{asset_base}assets/logos/sejong.svg", quote=True)

    if is_active:
        top_message = (
            f"<p class=\"lead\">{safe_member_line}</p>"
            f"<p class=\"support\">{safe_sub_line}</p>"
        )
    else:
        top_message = (
            f"<p class=\"lead warning\">{safe_warning_line}</p>"
            f"<p class=\"support\">{safe_inactive_message}</p>"
        )

    body = (
        "<div class=\"page\">"
        "<header class=\"card header\">"
        "<div class=\"logos\">"
        f"<img class=\"logo\" src=\"{kda_logo}\" alt=\"대한치과의사협회 로고\">"
        f"<img class=\"logo\" src=\"{sejong_logo}\" alt=\"세종시 로고\">"
        "</div>"
        f"<span class=\"badge {'active' if is_active else 'inactive'}\">{safe_badge}</span>"
        "</header>"
        "<section class=\"card\">"
        f"{top_message}"
        "</section>"
        "<section class=\"card\">"
        "<h2 class=\"section-title\">치과 정보</h2>"
        "<div class=\"info-row\">"
        "<span class=\"label\">치과명</span>"
        f"<span class=\"value\">{safe_name}</span>"
        "</div>"
        "<div class=\"info-row\">"
        "<span class=\"label\">대표원장</span>"
        f"<span class=\"value\">{director_html}</span>"
        "</div>"
        "<div class=\"info-row\">"
        "<span class=\"label\">주소</span>"
        f"<span class=\"value\">{address_html}</span>"
        "</div>"
        "<details class=\"details\">"
        "<summary>추가 정보(선택)</summary>"
        "<div class=\"detail-row\">"
        "<span class=\"label\">전화</span>"
        f"<span class=\"value\">{phone_html}</span>"
        "</div>"
        "<div class=\"detail-row\">"
        "<span class=\"label\">홈페이지</span>"
        f"<span class=\"value\">{homepage_html}</span>"
        "</div>"
        "</details>"
        "</section>"
        "<section class=\"card\">"
        "<h2 class=\"section-title\">세종시 치과의사회가 보증하는 가치</h2>"
        "<ul class=\"checklist\">"
        "<li>윤리 진료 준수</li>"
        "<li>지속적인 학술 활동: 정기 학술대회 및 최신 치료 교육 이수</li>"
        "<li>지역사회 공헌: 시민 구강검진, 취약계층 봉사활동 참여</li>"
        "</ul>"
        "<p class=\"emphasis\">세종시 치과의사회는 회원 한 분 한 분의 전문성과 책임감으로 "
        "세종시 치과 의료의 기준을 만들어갑니다.</p>"
        "</section>"
        "<section class=\"card\">"
        "<h2 class=\"section-title\">관련 링크</h2>"
        f"{_render_external_links()}"
        "</section>"
        "<footer class=\"foot\">"
        f"<span>유효기간: {safe_validity}</span>"
        f"<span>최종 업데이트: {safe_updated}</span>"
        f"<span>확인 코드: {safe_id}</span>"
        "</footer>"
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
        "line-height:1.6;margin:0;background:#f2f4f7;color:#1a1a1a;}"
        ".wrap{max-width:720px;margin:0 auto;padding:20px 16px;}"
        "h1{font-size:1.75rem;margin:0 0 10px;}"
        "h2{font-size:1.2rem;margin:0 0 12px;}"
        "p{margin:0 0 12px;}"
        ".page{display:flex;flex-direction:column;gap:14px;}"
        ".card{background:#fff;border-radius:16px;padding:16px 18px;"
        "box-shadow:0 8px 20px rgba(15,23,42,0.08);}"
        ".header{display:flex;align-items:center;justify-content:space-between;gap:12px;}"
        ".logos{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}"
        ".logo{height:32px;max-width:140px;object-fit:contain;}"
        ".badge{display:inline-flex;align-items:center;justify-content:center;"
        "padding:6px 12px;border-radius:999px;font-size:0.95rem;font-weight:700;}"
        ".badge.active{background:#e6f4ea;color:#166534;}"
        ".badge.inactive{background:#ffecec;color:#b00020;}"
        ".lead{font-size:1.05rem;font-weight:700;color:#111;}"
        ".lead.warning{color:#b00020;}"
        ".support{color:#374151;font-size:0.98rem;}"
        ".section-title{font-weight:700;color:#111;margin-bottom:8px;}"
        ".info-row,.detail-row{display:flex;flex-direction:column;gap:6px;"
        "padding:10px 0;border-bottom:1px solid #eef0f3;}"
        ".info-row:last-of-type{border-bottom:none;}"
        ".label{color:#4b5563;font-weight:600;font-size:0.95rem;}"
        ".value{color:#111;word-break:break-word;}"
        ".details{margin-top:10px;border-top:1px dashed #e5e7eb;padding-top:10px;}"
        ".details summary{cursor:pointer;font-weight:600;color:#1f2937;}"
        ".details[open] summary{margin-bottom:8px;}"
        ".checklist{list-style:none;padding:0;margin:0 0 12px;}"
        ".checklist li{padding-left:26px;position:relative;margin-bottom:8px;color:#111;}"
        ".checklist li::before{content:\"✔\";position:absolute;left:0;top:0;color:#16a34a;}"
        ".emphasis{font-weight:700;color:#1f2937;}"
        ".link-list{display:flex;flex-direction:column;gap:10px;}"
        ".link-item a{color:#1d4ed8;text-decoration:none;font-weight:600;}"
        ".link-item a:hover{text-decoration:underline;}"
        ".link-url{display:block;color:#6b7280;font-size:0.9rem;}"
        ".foot{display:flex;flex-direction:column;gap:6px;color:#6b7280;font-size:0.9rem;"
        "padding:4px 2px;}"
        ".zip-list{padding-left:18px;}"
        ".zip-list li{margin:6px 0;}"
        "@media (min-width:720px){"
        "h1{font-size:2.1rem;}"
        "h2{font-size:1.3rem;}"
        ".wrap{padding:32px 24px;}"
        ".info-row,.detail-row{flex-direction:row;align-items:flex-start;}"
        ".label{min-width:140px;}"
        ".foot{flex-direction:row;gap:18px;flex-wrap:wrap;}"
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

    parsed = urlparse(raw)
    if parsed.scheme:
        if parsed.scheme not in {"http", "https"}:
            return html.escape(raw)
        link = raw
        display = raw
    else:
        link = f"https://{raw}"
        display = link

    safe_link = html.escape(link, quote=True)
    safe_display = html.escape(display)
    return (
        f"<a href=\"{safe_link}\" target=\"_blank\" rel=\"noopener noreferrer\">"
        f"{safe_display}</a>"
    )


def _render_external_links() -> str:
    links = [
        ("충남치과의사회", "https://www.cndental.or.kr"),
        ("대한치과의사협회", "https://www.kda.or.kr"),
    ]
    items = []
    for label, url in links:
        safe_label = html.escape(label)
        safe_url = html.escape(url, quote=True)
        safe_display = html.escape(url)
        items.append(
            "<div class=\"link-item\">"
            f"<a href=\"{safe_url}\" target=\"_blank\" rel=\"noopener noreferrer\">"
            f"{safe_label}</a>"
            f"<span class=\"link-url\">{safe_display}</span>"
            "</div>"
        )
    return "<div class=\"link-list\">" + "".join(items) + "</div>"


def _choose_josa(text: str) -> str:
    if not text:
        return "는"
    last_char = text.strip()[-1]
    code = ord(last_char)
    if 0xAC00 <= code <= 0xD7A3:
        return "은" if (code - 0xAC00) % 28 else "는"
    return "는"


def _asset_base(cfg: AppConfig) -> str:
    prefix = cfg.path_prefix.strip("/")
    depth = len(prefix.split("/")) if prefix else 0
    depth += 1
    return "../" * depth
