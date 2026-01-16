"""HTML rendering helpers for static pages."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse, quote

from .config import AppConfig


ICON_PHONE = (
    "<svg class=\"btn-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
    " stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
    "<path d=\"M22 16.92V21a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07"
    " 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 3 5.18 2 2 0 0 1 5 3h4.09"
    " a2 2 0 0 1 2 1.72l.57 3.23a2 2 0 0 1-.45 1.73L10 11a16 16"
    " 0 0 0 6.73 6.73l1.32-1.21a2 2 0 0 1 1.73-.45l3.23.57a2 2"
    " 0 0 1 1.72 2z\"/></svg>"
)

ICON_MAP = (
    "<svg class=\"btn-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
    " stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
    "<path d=\"M12 21s7-4.35 7-10a7 7 0 0 0-14 0c0 5.65 7 10 7 10z\"/>"
    "<circle cx=\"12\" cy=\"11\" r=\"3\"/></svg>"
)

ICON_SEAL = (
    "<svg class=\"seal-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
    " stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
    "<circle cx=\"12\" cy=\"12\" r=\"9\"/>"
    "<path d=\"M8.5 12l2.5 2.5 4.5-4.5\"/></svg>"
)


def render_root_index(cfg: AppConfig) -> str:
    body = (
        "<div class=\"card empty-state\">"
        "<div class=\"icon-area\">QR</div>"
        "<h1>안내 페이지</h1>"
        "<p>치과별 QR 코드 전용 안내 페이지입니다.<br>개별 QR 코드를 스캔해주세요.</p>"
        "</div>"
    )
    return _render_page(cfg, title="QR 안내", body=body)


def render_404(cfg: AppConfig) -> str:
    body = (
        "<div class=\"card empty-state error\">"
        "<div class=\"icon-area\">!</div>"
        "<h1>유효하지 않은 코드</h1>"
        "<p>요청하신 페이지를 찾을 수 없거나<br>잘못된 접근입니다.</p>"
        "</div>"
    )
    return _render_page(cfg, title="페이지 없음", body=body)


def render_outbox_index(cfg: AppConfig, build_timestamp: str, zip_names: list[str]) -> str:
    items = "".join(
        f"<li><a href=\"zips/{html.escape(name, quote=True)}\" class=\"file-link\">"
        f"<span class=\"file-icon\">ZIP</span> {html.escape(name)}</a></li>"
        for name in zip_names
    )
    if not items:
        items = "<li class=\"empty-list\">다운로드 가능한 파일이 없습니다.</li>"

    body = (
        "<div class=\"card\">"
        "<h1 class=\"page-title\">Outbox 다운로드</h1>"
        f"<p class=\"meta-info\">최종 업데이트: {html.escape(build_timestamp)}</p>"
        "<div class=\"action-area\">"
        "<a href=\"sendlist.csv\" class=\"btn btn-primary\">sendlist.csv 다운로드</a>"
        "</div>"
        "</div>"
        "<div class=\"card\">"
        "<h2 class=\"section-title\">파일 목록</h2>"
        f"<ul class=\"zip-list\">{items}</ul>"
        "</div>"
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
    badge_text = "정회원" if is_active else "미확인"
    validity = f"{cfg.year}-01-01 ~ {cfg.year}-12-31"

    josa = _choose_josa(clinic_name)
    member_line = (
        f"<strong>{html.escape(clinic_name)}</strong>{josa} {cfg.year}년<br>"
        "<strong>'세종특별자치시 치과의사회'</strong> 정회원입니다."
    )
    sub_line = "세종시 치과의사회는 시민의 구강건강을 지키는 공식 치과의사 단체입니다."
    warning_line = "현재 정회원으로 확인되지 않습니다."

    safe_name = html.escape(clinic_name)
    safe_badge = html.escape(badge_text)
    safe_validity = html.escape(validity)
    safe_updated = html.escape(build_timestamp)

    safe_sub_line = html.escape(sub_line)
    safe_warning_line = html.escape(warning_line)
    safe_inactive_message = html.escape(cfg.message_inactive)

    address_html = _render_address_link(address, clinic_name)
    director_html = html.escape(_display_or_dash(director))
    phone_html = _render_tel_link(phone)
    homepage_html = _render_homepage(homepage)

    asset_base = _asset_base(cfg)
    kda_logo = html.escape(f"{asset_base}assets/logos/kda.jpg", quote=True)
    sejong_logo = html.escape(f"{asset_base}assets/logos/sejong.jpg", quote=True)

    if is_active:
        top_message = (
            "<div class=\"status-message success\">"
            f"<p class=\"main-msg\">{member_line}</p>"
            f"<p class=\"sub-msg\">{safe_sub_line}</p>"
            "</div>"
        )
        badge_class = "active"
    else:
        top_message = (
            "<div class=\"status-message warning\">"
            f"<p class=\"main-msg\">{safe_warning_line}</p>"
            f"<p class=\"sub-msg\">{safe_inactive_message}</p>"
            "</div>"
        )
        badge_class = "inactive"

    seal_html = f"<span class=\"seal\">{ICON_SEAL}공식 인증</span>" if is_active else ""
    cert_row = (
        "<div class=\"cert-row\">"
        "<div class=\"cert-badges\">"
        f"<span class=\"badge {badge_class}\">{safe_badge}</span>"
        f"{seal_html}"
        "</div>"
        f"<p class=\"validity-inline\">유효기간: {safe_validity}</p>"
        "</div>"
    )

    tel_digits = _sanitize_tel(phone)
    tel_button = ""
    if tel_digits:
        tel_href = html.escape(f"tel:{tel_digits}", quote=True)
        tel_button = (
            f"<a href=\"{tel_href}\" class=\"btn btn-primary\">"
            f"{ICON_PHONE}<span>전화하기</span></a>"
        )

    address_value = (address or "").strip()
    query = address_value if address_value else clinic_name.strip()
    map_url = _naver_map_search_url(query)
    map_button = ""
    if map_url:
        map_href = html.escape(map_url, quote=True)
        map_button = (
            f"<a href=\"{map_href}\" class=\"btn btn-secondary\" target=\"_blank\""
            f" rel=\"noopener noreferrer\">{ICON_MAP}<span>네이버 지도</span></a>"
        )

    cta_buttons = "".join(button for button in [tel_button, map_button] if button)
    cta_row = f"<div class=\"cta-row\">{cta_buttons}</div>" if cta_buttons else ""

    body = (
        "<div class=\"page-container\">"
        "<header class=\"card header-card\">"
        "<div class=\"header-top\">"
        "<div class=\"logos\">"
        f"<img class=\"logo\" src=\"{kda_logo}\" alt=\"대한치과의사협회\">"
        f"<img class=\"logo\" src=\"{sejong_logo}\" alt=\"세종시치과의사회\">"
        "</div>"
        "</div>"
        f"{cert_row}"
        f"{top_message}"
        f"{cta_row}"
        "</header>"
        "<section class=\"card info-card\">"
        "<h2 class=\"section-title\">치과 정보</h2>"
        "<div class=\"info-grid\">"
        "<div class=\"info-item\">"
        "<span class=\"label\">치과명</span>"
        f"<span class=\"value highlight\">{safe_name}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">대표원장</span>"
        f"<span class=\"value\">{director_html}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">주소</span>"
        f"<span class=\"value\">{address_html}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">전화번호</span>"
        f"<span class=\"value phone\">{phone_html}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">홈페이지</span>"
        f"<span class=\"value\">{homepage_html}</span>"
        "</div>"
        "</div>"
        "</section>"
        "<section class=\"card value-card\">"
        "<h2 class=\"section-title\">세종시 치과의사회가 보증하는 가치</h2>"
        "<ul class=\"checklist\">"
        "<li><strong>윤리 진료 준수</strong><span>원칙을 지키는 책임 진료</span></li>"
        "<li><strong>지속적인 학술 활동</strong><span>정기 학술대회 및 최신 임상 교육 이수</span></li>"
        "<li><strong>지역사회 공헌</strong><span>시민 구강검진, 취약계층 봉사활동 참여</span></li>"
        "</ul>"
        "<div class=\"emphasis-box\">"
        "<p>회원 한 분 한 분의 전문성과 책임감으로<br>세종시 치과 의료의 기준을 만들어갑니다.</p>"
        "</div>"
        "</section>"
        "<section class=\"card link-card\">"
        "<h2 class=\"section-title\">관련 링크</h2>"
        f"{_render_external_links()}"
        "</section>"
        "<footer class=\"footer\">"
        f"<p class=\"validity\">유효기간: {safe_validity}</p>"
        f"<p class=\"updated\">정보 업데이트: {safe_updated}</p>"
        "</footer>"
        "</div>"
    )
    return _render_page(cfg, title=safe_name, body=body)


def _render_page(cfg: AppConfig, title: str, body: str) -> str:
    safe_title = html.escape(title)
    robots = _render_robots(cfg.noindex)

    css = (
        ":root{"
        "--primary:#2563eb;--primary-dark:#1e40af;--bg-color:#f8fafc;"
        "--card-bg:#ffffff;--text-main:#1e293b;--text-sub:#64748b;"
        "--border:#e2e8f0;--success-bg:#ecfdf5;--success-text:#047857;"
        "--warning-bg:#fef2f2;--warning-text:#b91c1c;"
        "--shadow:0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);"
        "}"
        "*{box-sizing:border-box}body{font-family:'Pretendard',-apple-system,BlinkMacSystemFont,system-ui,Roboto,sans-serif;line-height:1.6;margin:0;background:var(--bg-color);color:var(--text-main);-webkit-text-size-adjust:100%}"
        ".wrap{max-width:600px;margin:0 auto;padding:20px 16px}"
        "h1,h2,p{margin:0}a{text-decoration:none;color:inherit}"
        ".page-container{display:flex;flex-direction:column;gap:16px}"
        ".section-title{font-size:1.1rem;font-weight:700;color:var(--text-main);margin-bottom:12px;padding-left:4px}"
        ".card{background:var(--card-bg);border-radius:16px;padding:24px 20px;box-shadow:var(--shadow);border:1px solid rgba(0,0,0,0.02)}"
        ".header-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}"
        ".logos{display:flex;align-items:center;gap:12px}"
        ".logo{height:36px;width:auto;object-fit:contain}"
        ".cert-row{display:flex;flex-direction:column;gap:8px;margin-bottom:16px}"
        ".cert-badges{display:flex;align-items:center;gap:8px;flex-wrap:wrap}"
        ".badge{font-size:0.85rem;font-weight:700;padding:6px 12px;border-radius:20px;letter-spacing:-0.5px;white-space:nowrap}"
        ".badge.active{background:var(--success-bg);color:var(--success-text)}"
        ".badge.inactive{background:var(--warning-bg);color:var(--warning-text)}"
        ".seal{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;border:1px dashed #1e40af;background:#eef2ff;color:#1e40af;font-size:0.8rem;font-weight:700}"
        ".seal-ico{width:14px;height:14px}"
        ".validity-inline{margin:0;font-size:0.85rem;color:var(--text-sub)}"
        ".status-message{text-align:left;padding:12px 14px;border-radius:12px;border:1px solid var(--border)}"
        ".status-message.success{background:var(--success-bg)}"
        ".status-message.warning{background:var(--warning-bg)}"
        ".main-msg{font-size:1.15rem;font-weight:400;color:var(--text-main);line-height:1.5;margin:0 0 6px 0}"
        ".main-msg strong{font-weight:700;color:var(--primary-dark)}"
        ".sub-msg{font-size:0.9rem;color:var(--text-sub);margin:0}"
        ".status-message.warning .main-msg{color:var(--warning-text);font-weight:700}"
        ".cta-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}"
        ".btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 14px;border-radius:12px;font-weight:700;font-size:0.95rem;border:1px solid transparent;width:100%}"
        ".btn-ico{width:18px;height:18px}"
        ".btn-primary{background:var(--primary);color:white}"
        ".btn-primary:hover{background:var(--primary-dark)}"
        ".btn-secondary{background:#eef2ff;color:#1e40af;border-color:#c7d2fe}"
        ".btn-secondary:hover{background:#e0e7ff}"
        "a:focus-visible,.btn:focus-visible{outline:2px solid var(--primary);outline-offset:2px}"
        ".info-grid{display:flex;flex-direction:column;gap:16px}"
        ".info-item{display:flex;flex-direction:column;gap:4px;border-bottom:1px solid var(--border);padding-bottom:12px}"
        ".info-item:last-child{border-bottom:none;padding-bottom:0}"
        ".label{font-size:0.85rem;color:var(--text-sub);font-weight:500}"
        ".value{font-size:1rem;color:var(--text-main);font-weight:500;overflow-wrap:anywhere;word-break:break-word}"
        ".value.highlight{font-size:1.1rem;font-weight:700}"
        ".value.phone{font-family:monospace,sans-serif;letter-spacing:0.5px;font-weight:600}"
        ".tel-link,.map-link{color:var(--primary);font-weight:700}"
        ".tel-link:hover,.map-link:hover{text-decoration:underline}"
        ".value a{color:var(--primary);font-weight:600}"
        ".checklist{list-style:none;padding:0;margin:0}"
        ".checklist li{position:relative;padding-left:28px;margin-bottom:16px}"
        ".checklist li:last-child{margin-bottom:0}"
        ".checklist li::before{content:'';position:absolute;left:0;top:4px;width:18px;height:18px;background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E\");background-repeat:no-repeat;background-position:center}"
        ".checklist strong{display:block;color:var(--text-main);margin-bottom:0;line-height:1.15}"
        ".checklist span{font-size:0.9rem;color:var(--text-sub);line-height:1.15;display:block}"
        ".emphasis-box{margin-top:20px;background:#f1f5f9;padding:16px;border-radius:12px;text-align:center}"
        ".emphasis-box p{font-size:0.9rem;color:var(--text-main);font-weight:600;line-height:1.5}"
        ".link-list{display:grid;grid-template-columns:1fr;gap:12px}"
        ".link-item{display:flex;flex-direction:column;align-items:center;text-align:center;background:#f8fafc;padding:12px;border-radius:12px;border:1px solid var(--border);transition:transform 0.2s}"
        ".link-item:active{transform:scale(0.98)}"
        ".link-item a{font-weight:600;font-size:0.95rem;color:var(--text-main);margin-bottom:4px;display:block;width:100%}"
        ".link-url{font-size:0.75rem;color:var(--text-sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}"
        ".footer{margin-top:24px;text-align:center;color:#94a3b8;font-size:0.8rem}"
        ".footer p{margin-bottom:4px}"
        ".empty-state{text-align:center;padding:40px 20px}"
        ".icon-area{font-size:2rem;font-weight:900;color:#cbd5e1;margin-bottom:16px}"
        ".empty-state.error .icon-area{color:#fca5a5}"
        ".zip-list{list-style:none;padding:0}"
        ".zip-list li{margin-bottom:8px}"
        ".file-link{display:flex;align-items:center;padding:10px;background:#f1f5f9;border-radius:8px;color:var(--text-main)}"
        ".file-icon{background:var(--text-sub);color:white;font-size:0.7rem;padding:2px 6px;border-radius:4px;margin-right:8px;font-weight:700}"
        "@media (max-width:360px){.cta-row{grid-template-columns:1fr}}"
        "@media (min-width:420px){.link-list{grid-template-columns:1fr 1fr}}"
        "@media (min-width:640px){"
        ".wrap{padding:40px 20px}"
        ".info-grid{display:grid;grid-template-columns:auto 1fr;column-gap:24px;row-gap:16px}"
        ".info-item{flex-direction:row;align-items:baseline;padding-bottom:16px}"
        ".label{width:100px;flex-shrink:0}"
        ".cert-row{flex-direction:row;align-items:center;justify-content:space-between}"
        "}"
    )

    return (
        "<!doctype html>"
        "<html lang=\"ko\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"{robots}"
        f"<title>{safe_title}</title>"
        f"<style>{css}</style>"
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


def _sanitize_tel(phone: str) -> str:
    return re.sub(r"[^0-9+]", "", phone or "")


def _render_tel_link(phone: str) -> str:
    raw = (phone or "").strip()
    if not raw:
        return "-"

    digits = _sanitize_tel(raw)
    if not digits:
        return html.escape(raw)

    href = html.escape(f"tel:{digits}", quote=True)
    display = html.escape(raw)
    return f"<a href=\"{href}\" class=\"tel-link\">{display}</a>"


def _naver_map_search_url(query: str) -> str:
    cleaned = (query or "").strip()
    if not cleaned:
        return ""
    return f"https://map.naver.com/v5/search/{quote(cleaned, safe='')}"


def _render_address_link(address: str, clinic_name: str) -> str:
    raw = (address or "").strip()
    if not raw:
        return "-"

    query = raw
    url = _naver_map_search_url(query)
    if not url:
        return html.escape(raw)

    safe_url = html.escape(url, quote=True)
    safe_text = html.escape(raw)
    return (
        f"<a href=\"{safe_url}\" class=\"map-link\" target=\"_blank\" rel=\"noopener noreferrer\">"
        f"{safe_text}</a>"
    )


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

    display_clean = safe_display.replace("https://", "").replace("http://", "").rstrip("/")

    return (
        f"<a href=\"{safe_link}\" target=\"_blank\" rel=\"noopener noreferrer\">"
        f"{display_clean}</a>"
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
        items.append(
            "<div class=\"link-item\">"
            f"<a href=\"{safe_url}\" target=\"_blank\" rel=\"noopener noreferrer\">"
            f"{safe_label}</a>"
            f"<span class=\"link-url\">외부 링크 이동</span>"
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
