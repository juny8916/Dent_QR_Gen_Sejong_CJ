"""
정적 HTML 렌더링(templates) 모듈.

- 무엇(What): 치과 페이지(clinic page), 루트/404, outbox 인덱스 HTML을 생성한다.
- 왜(Why): GitHub Pages 배포용 정적 사이트(static site)를 만들기 위함.
- 어떻게(How): 외부 입력은 모두 HTML escape 처리하고, CTA 우선 UI로 환자 행동을 유도한다.

주의: 이 시스템은 환자 개인정보를 수집/저장하지 않으며,
필요 최소한의 clinic_id 이벤트만(옵션) 분석용으로 전송한다.
"""

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

ICON_HOME = (
    "<svg class=\"btn-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
    " stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
    "<path d=\"M3 11l9-8 9 8\"/><path d=\"M5 10v10h14V10\"/>"
    "<path d=\"M9 20v-6h6v6\"/></svg>"
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


# -----------------------------------------------------------------------------
# [WHY] 환자가 QR 스캔 직후 신뢰(정회원 인증) → 행동(전화/지도/홈페이지)으로 이어지도록 설계한다.
# [WHAT] 치과별 랜딩 페이지 HTML을 반환한다(docs/c/<clinic_id>/index.html).
# [HOW] 인증 정보 → (가이드) → CTA → 안내 메시지 → 상세 정보 순으로 배치한다.
#       링크는 tel:/네이버지도/홈페이지 규칙을 따르며, 외부 입력은 escape 처리한다.
# -----------------------------------------------------------------------------
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

    # WARNING: 엑셀에서 들어온 문자열은 반드시 escape 처리하여 XSS를 방지한다.
    safe_name = html.escape(clinic_name)
    safe_badge = html.escape(badge_text)
    safe_validity = html.escape(validity)
    safe_updated = html.escape(build_timestamp)
    safe_clinic_id_attr = html.escape(clinic_id, quote=True)

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
    brand_meta = (
        "<div class=\"brand-meta\">"
        f"<span class=\"badge {badge_class}\">{safe_badge}</span>"
        f"{seal_html}"
        "</div>"
    )
    validity_inline = f"<p class=\"validity-inline\">인증기간: {safe_validity}</p>"

    tel_digits = _sanitize_tel(phone)
    tel_button = ""
    if tel_digits:
        tel_href = html.escape(f"tel:{tel_digits}", quote=True)
        tel_button = (
            f"<a href=\"{tel_href}\" class=\"btn btn-primary\" data-analytics-event=\"click_call\""
            f" data-clinic-id=\"{safe_clinic_id_attr}\">{ICON_PHONE}<span>전화상담</span></a>"
        )

    address_value = (address or "").strip()
    query = address_value if address_value else clinic_name.strip()
    map_url = _naver_map_search_url(query)
    map_button = ""
    if map_url:
        map_href = html.escape(map_url, quote=True)
        map_button = (
            f"<a href=\"{map_href}\" class=\"btn btn-secondary\" target=\"_blank\""
            f" rel=\"noopener noreferrer\" data-analytics-event=\"click_map\""
            f" data-clinic-id=\"{safe_clinic_id_attr}\">{ICON_MAP}<span>지도보기</span></a>"
        )

    homepage_url = _homepage_url(homepage)
    homepage_button = ""
    if homepage_url:
        homepage_href = html.escape(homepage_url, quote=True)
        homepage_button = (
            f"<a href=\"{homepage_href}\" class=\"btn btn-tertiary\" target=\"_blank\""
            f" rel=\"noopener noreferrer\" data-analytics-event=\"click_homepage\""
            f" data-clinic-id=\"{safe_clinic_id_attr}\">{ICON_HOME}<span>홈페이지</span></a>"
        )

    cta_buttons = "".join(button for button in [tel_button, map_button, homepage_button] if button)
    cta_row = f"<div class=\"cta-row\">{cta_buttons}</div>" if cta_buttons else ""
    action_guide = (
        "<p class=\"action-guide\">진료 문의 및 예약은 위 버튼을 이용하세요.</p>"
        if is_active and cta_row
        else ""
    )
    action_section = (
        f"<section class=\"section-action\">{cta_row}{action_guide}</section>"
        if cta_row or action_guide
        else ""
    )

    body = (
        f"<div class=\"page-container\" data-page-type=\"clinic\" data-clinic-id=\"{safe_clinic_id_attr}\">"
        "<header class=\"section-brand\">"
        f"<h1 class=\"clinic-title\">{safe_name}</h1>"
        f"{brand_meta}"
        f"{validity_inline}"
        "</header>"
        f"{action_section}"
        f"{top_message}"
        "<section class=\"card info-card\">"
        "<div class=\"info-grid\">"
        "<div class=\"info-item\">"
        "<span class=\"label\">대표원장</span>"
        f"<span class=\"value\">{director_html}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">전화번호</span>"
        f"<span class=\"value phone\">{phone_html}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">주소</span>"
        f"<span class=\"value\">{address_html}</span>"
        "</div>"
        "<div class=\"info-item\">"
        "<span class=\"label\">홈페이지</span>"
        f"<span class=\"value\">{homepage_html}</span>"
        "</div>"
        "</div>"
        "</section>"
        "<section class=\"card value-card\">"
        "<h2 class=\"section-title\">세종시 치과의사회가 보증하는 가치</h2>"
        "<ul class=\"value-list\">"
        "<li class=\"value-item\">"
        "<div class=\"value-icon-box\">"
        "<svg class=\"check-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
        " stroke=\"currentColor\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<polyline points=\"20 6 9 17 4 12\"/></svg>"
        "</div>"
        "<div class=\"value-text\">"
        "<strong class=\"value-head\">윤리 진료 준수</strong>"
        "<span class=\"value-desc\">원칙을 지키는 책임 진료</span>"
        "</div>"
        "</li>"
        "<li class=\"value-item\">"
        "<div class=\"value-icon-box\">"
        "<svg class=\"check-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
        " stroke=\"currentColor\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<polyline points=\"20 6 9 17 4 12\"/></svg>"
        "</div>"
        "<div class=\"value-text\">"
        "<strong class=\"value-head\">지속적인 학술 활동</strong>"
        "<span class=\"value-desc\">정기 학술대회 및 최신 임상 교육 이수</span>"
        "</div>"
        "</li>"
        "<li class=\"value-item\">"
        "<div class=\"value-icon-box\">"
        "<svg class=\"check-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
        " stroke=\"currentColor\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
        "<polyline points=\"20 6 9 17 4 12\"/></svg>"
        "</div>"
        "<div class=\"value-text\">"
        "<strong class=\"value-head\">지역사회 공헌</strong>"
        "<span class=\"value-desc\">시민 구강검진, 취약계층 봉사활동 참여</span>"
        "</div>"
        "</li>"
        "</ul>"
        "</section>"
        "<footer class=\"section-footer\">"
        "<div class=\"official-logos\">"
        f"<img class=\"logo-grayscale\" src=\"{kda_logo}\" alt=\"대한치과의사협회\">"
        f"<img class=\"logo-grayscale\" src=\"{sejong_logo}\" alt=\"세종시치과의사회\">"
        "</div>"
        "<p class=\"footer-msg\">본 페이지는 <strong>세종특별자치시 치과의사회</strong>가<br>"
        "공식 정보를 보증하는 의료기관 안내입니다.</p>"
        "<div class=\"footer-meta\">"
        f"<span>인증기간: {safe_validity}</span>"
        f"<span>Updated: {safe_updated}</span>"
        "</div>"
        f"{_render_external_links()}"
        "</footer>"
        "</div>"
    )
    return _render_page(cfg, title=safe_name, body=body)


def _render_page(cfg: AppConfig, title: str, body: str) -> str:
    safe_title = html.escape(title)
    robots = _render_robots(cfg.noindex)
    analytics = _render_analytics(cfg)

    css = (
        ":root{"
        "--primary:#172554;--primary-light:#1e3a8a;"
        "--bg-color:#f8fafc;"
        "--surface:#ffffff;"
        "--surface-border:#e2e8f0;"
        "--text-main:#0f172a;--text-sub:#334155;--text-light:#64748b;"
        "--success-bg:#f0fdfa;--success-text:#115e59;"
        "--warning-bg:#fef2f2;--warning-text:#b91c1c;"
        "--shadow-card:0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);"
        "}"
        "*{box-sizing:border-box}body{font-family:'Pretendard',-apple-system,BlinkMacSystemFont,system-ui,Roboto,sans-serif;line-height:1.6;margin:0;color:var(--text-main);background:var(--bg-color);-webkit-text-size-adjust:100%}"
        ".wrap{max-width:480px;margin:0 auto;padding:0;min-height:100vh;display:flex;flex-direction:column;position:relative;background:#f8fafc}"
        ".page-container{padding:40px 24px;display:flex;flex-direction:column;gap:28px;flex:1;position:relative;z-index:1}"
        "a{text-decoration:none;color:inherit;transition:all 0.2s}"
        ".section-brand{text-align:left;padding:8px 0}"
        ".clinic-title{font-size:2rem;font-weight:800;letter-spacing:-0.03em;color:var(--text-main);margin:0 0 10px 0;line-height:1.2;word-break:keep-all}"
        ".brand-meta{display:flex;align-items:center;gap:8px}"
        ".badge{font-size:0.75rem;font-weight:700;padding:5px 10px;border-radius:6px;letter-spacing:-0.2px;text-transform:uppercase}"
        ".badge.active{background:var(--primary);color:#fff;border:1px solid var(--primary)}"
        ".badge.inactive{background:var(--warning-bg);color:var(--warning-text);border:1px solid #fee2e2}"
        ".seal{display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;font-weight:700;color:var(--primary);background:#fff;padding:5px 10px;border-radius:6px;border:1px solid #e2e8f0;box-shadow:0 1px 2px rgba(0,0,0,0.03)}"
        ".seal-ico{width:12px;height:12px;color:var(--primary)}"
        ".validity-inline{font-size:0.8rem;color:var(--text-light);margin:6px 0 0 0}"
        ".cta-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}"
        ".cta-row > .btn:first-child{grid-column:span 2}"
        ".btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:16px;border-radius:12px;font-weight:700;font-size:1rem;border:none;cursor:pointer;position:relative;overflow:hidden;transition:background 0.1s}"
        ".btn:active{opacity:0.9}"
        ".btn-primary{background:var(--primary);color:white;box-shadow:0 4px 10px rgba(23, 37, 84, 0.2)}"
        ".btn-secondary{background:#fff;color:var(--text-main);border:1px solid #cbd5e1;box-shadow:var(--shadow-card)}"
        ".btn-tertiary{background:transparent;color:var(--text-sub);border:1px solid transparent;text-decoration:underline;text-underline-offset:4px;text-decoration-color:#cbd5e1}"
        ".btn-ico{width:20px;height:20px}"
        ".action-guide{font-size:0.9rem;color:var(--text-sub);text-align:center;margin-top:16px;font-weight:600}"
        ".status-message{padding:20px;border-radius:12px;font-size:1rem;line-height:1.6;background:#fff;border:1px solid #e2e8f0;box-shadow:var(--shadow-card)}"
        ".status-message.success{border-left:4px solid var(--primary);background:#f1f5f9}"
        ".status-message.warning{background:#fff1f2;border-left:4px solid var(--warning-text)}"
        ".main-msg{margin:0;color:var(--text-main)}"
        ".main-msg strong{color:var(--primary);font-weight:800}"
        ".sub-msg{margin:8px 0 0 0;font-size:0.9rem;color:var(--text-sub);line-height:1.5;padding-top:8px;border-top:1px dashed #cbd5e1}"
        ".card{background:var(--surface);border-radius:16px;padding:28px 24px;box-shadow:var(--shadow-card);border:1px solid var(--surface-border)}"
        ".info-grid{display:flex;flex-direction:column;gap:18px}"
        ".info-item{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:14px;border-bottom:1px solid #e2e8f0}"
        ".info-item:last-child{border-bottom:none;padding-bottom:0}"
        ".label{font-size:0.95rem;color:var(--text-sub);font-weight:600;width:70px;flex-shrink:0;padding-top:2px}"
        ".value{font-size:1rem;color:var(--text-main);font-weight:600;text-align:right;word-break:keep-all;line-height:1.5}"
        ".value.phone{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700;letter-spacing:0.02em;color:var(--text-main);font-size:1.05rem}"
        ".value a{color:var(--primary-light);text-decoration:underline;text-underline-offset:3px}"
        ".tel-link,.map-link{color:var(--primary-light)}"
        ".section-title{font-size:1.1rem;font-weight:800;color:var(--text-main);margin-bottom:18px;letter-spacing:-0.01em}"
        ".value-list{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:16px}"
        ".value-item{display:flex;gap:12px;align-items:flex-start}"
        ".value-icon-box{flex-shrink:0;width:24px;height:24px;display:flex;align-items:center;justify-content:center;color:#fff;margin-top:2px;background:var(--primary);border-radius:50%}"
        ".check-ico{width:14px;height:14px}"
        ".value-text{display:flex;flex-direction:column}"
        ".value-head{font-size:0.95rem;font-weight:700;color:var(--text-main);margin-bottom:2px}"
        ".value-desc{font-size:0.9rem;color:var(--text-sub);line-height:1.4}"
        ".section-footer{margin-top:auto;padding-top:40px;text-align:center}"
        ".official-logos{display:flex;justify-content:center;gap:16px;margin-bottom:24px;opacity:1;filter:none}"
        ".logo-grayscale{height:28px;width:auto;filter:grayscale(100%);opacity:0.7}"
        ".logo-placeholder{background:#e2e8f0;width:120px;height:32px;border-radius:4px}"
        ".footer-msg{font-size:0.75rem;color:var(--text-light);margin-bottom:20px;line-height:1.5}"
        ".footer-msg strong{color:var(--text-sub);font-weight:600}"
        ".footer-meta{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;font-size:0.7rem;color:var(--text-light);margin-bottom:28px}"
        ".link-list{display:flex;justify-content:center;gap:14px}"
        ".link-item a{font-size:0.75rem;color:var(--text-light);font-weight:500;text-decoration:underline;text-decoration-color:#cbd5e1}"
        ".link-url{display:none}"
        ".empty-state{text-align:center;padding:60px 20px}"
        ".icon-area{font-size:2.5rem;font-weight:900;color:#e2e8f0;margin-bottom:20px}"
        ".empty-state.error .icon-area{color:#fca5a5}"
        ".page-title{font-size:1.1rem;font-weight:800;color:var(--text-main);margin:0 0 12px 0}"
        ".meta-info{font-size:0.85rem;color:var(--text-light)}"
        ".action-area{margin-top:12px}"
        ".zip-list{list-style:none;padding:0;margin:0}"
        ".zip-list li{margin-bottom:8px}"
        ".file-link{display:flex;align-items:center;gap:8px;padding:10px 12px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;color:var(--text-main)}"
        ".file-icon{font-size:0.7rem;font-weight:700;background:var(--primary);color:#fff;padding:2px 6px;border-radius:4px}"
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
        f"{analytics}"
        "</head>"
        "<body>"
        "<main class=\"wrap\">"
        f"{body}"
        "</main>"
        "</body>"
        "</html>"
    )


# -----------------------------------------------------------------------------
# [WHY] GA4 활성화 시 clinic_id 단위의 최소 이벤트만 수집한다.
# [WHAT] gtag 스니펫 + qr_view / click_* 이벤트를 전송하는 스크립트를 삽입한다.
# [HOW] data-page-type="clinic" 에서만 동작하며, clinic_id가 없으면 전송하지 않는다.
# -----------------------------------------------------------------------------
def _render_analytics(cfg: AppConfig) -> str:
    if cfg.analytics_provider != "ga4":
        return ""

    measurement_id = cfg.ga4_measurement_id.strip()
    if not measurement_id:
        return ""

    safe_id_attr = html.escape(measurement_id, quote=True)
    safe_id_js = html.escape(measurement_id)
    return (
        f"<script async src=\"https://www.googletagmanager.com/gtag/js?id={safe_id_attr}\"></script>"
        "<script>"
        "window.dataLayer = window.dataLayer || [];"
        "function gtag(){dataLayer.push(arguments);}"
        "gtag('js', new Date());"
        f"gtag('config', '{safe_id_js}', {{'anonymize_ip': true}});"
        "(function(){"
        "if (typeof window.gtag !== 'function') {return;}"
        "document.addEventListener('DOMContentLoaded', function(){"
        "var container=document.querySelector('[data-page-type=\"clinic\"]');"
        "if (!container) {return;}"
        "var clinicId=container.getAttribute('data-clinic-id')||'';"
        "if (!clinicId) {return;}"
        "window.gtag('event','qr_view',{clinic_id:clinicId});"
        "var targets=container.querySelectorAll('[data-analytics-event]');"
        "targets.forEach(function(el){"
        "el.addEventListener('click', function(){"
        "var eventName=el.getAttribute('data-analytics-event');"
        "if (!eventName) {return;}"
        "window.gtag('event', eventName, {clinic_id:clinicId});"
        "});"
        "});"
        "});"
        "})();"
        "</script>"
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


# WARNING: 홈페이지 링크는 http/https만 허용하며, 스킴이 없으면 https:// 를 붙인다.
def _homepage_url(value: str) -> str:
    raw = value.strip() if value else ""
    if not raw:
        return ""

    parsed = urlparse(raw)
    if parsed.scheme:
        if parsed.scheme not in {"http", "https"}:
            return ""
        return raw
    return f"https://{raw}"


def _render_homepage(value: str) -> str:
    raw = value.strip() if value else ""
    if not raw:
        return "-"

    link = _homepage_url(raw)
    if not link:
        return html.escape(raw)
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
