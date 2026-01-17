"""
정적 HTML 렌더링(templates) 모듈.

- 무엇(What): 치과 페이지(clinic page), 루트/404, outbox 인덱스 HTML을 생성한다.
- 왜(Why): GitHub Pages 배포용 정적 사이트(static site)를 만들기 위함.
- 어떻게(How): 외부 입력은 모두 HTML escape 처리하고, CTA 우선 UI로 환자 행동을 유도한다.
- 디자인(v4.7): Refined Button Hierarchy (Solid -> Outlined -> Soft)

주의: 이 시스템은 환자 개인정보를 수집/저장하지 않으며,
필요 최소한의 clinic_id 이벤트만(옵션) 분석용으로 전송한다.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
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

ICON_CHECK = (
    "<svg class=\"check-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
    " stroke=\"currentColor\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
    "<polyline points=\"20 6 9 17 4 12\"/></svg>"
)

ICON_SAVE = (
    "<svg class=\"btn-ico\" aria-hidden=\"true\" viewBox=\"0 0 24 24\" fill=\"none\""
    " stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">"
    "<path d=\"M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z\"/>"
    "<polyline points=\"17 21 17 13 7 13 7 21\"/><polyline points=\"7 3 7 8 15 8\"/></svg>"
)

# 치과별 안내 위젯(챗봇) 데이터 경로: data/clinic_extra/<clinic_id>.json
_CLINIC_EXTRA_DIR = Path(__file__).resolve().parents[2] / "data" / "clinic_extra"


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
# [HOW] 인증 → CTA → 안내 메시지 → 정보 순으로 배치한다.
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

    tel_digits = _sanitize_tel(phone)
    tel_href = html.escape(f"tel:{tel_digits}", quote=True) if tel_digits else ""
    tel_button = ""
    if tel_href:
        tel_button = (
            f"<a href=\"{tel_href}\" class=\"btn btn-primary\" data-analytics-event=\"click_call\""
            f" data-clinic-id=\"{safe_clinic_id_attr}\">{ICON_PHONE}<span>전화상담</span></a>"
        )

    address_value = (address or "").strip()
    query = address_value if address_value else clinic_name.strip()
    map_url = _naver_map_search_url(query)
    map_href = html.escape(map_url, quote=True) if map_url else ""
    map_button = ""
    if map_href:
        map_button = (
            f"<a href=\"{map_href}\" class=\"btn btn-secondary\" target=\"_blank\""
            f" rel=\"noopener noreferrer\" data-analytics-event=\"click_map\""
            f" data-clinic-id=\"{safe_clinic_id_attr}\">{ICON_MAP}<span>지도보기</span></a>"
        )

    homepage_url = _homepage_url(homepage)
    homepage_href = html.escape(homepage_url, quote=True) if homepage_url else ""
    homepage_button = ""
    if homepage_href:
        homepage_button = (
            f"<a href=\"{homepage_href}\" class=\"btn btn-secondary\" target=\"_blank\""
            f" rel=\"noopener noreferrer\" data-analytics-event=\"click_homepage\""
            f" data-clinic-id=\"{safe_clinic_id_attr}\">{ICON_HOME}<span>홈페이지</span></a>"
        )

    cta_buttons = "".join(button for button in [tel_button, map_button, homepage_button] if button)
    cta_row = f"<div class=\"cta-row\">{cta_buttons}</div>" if cta_buttons else ""

    js_name = safe_name.replace("'", "\\'")
    js_tel = tel_digits
    js_addr = html.escape(address_value).replace("'", "\\'")

    save_contact_btn = (
        f"<button class=\"btn btn-soft btn-full\" onclick=\"saveContact('{js_name}', '{js_tel}', '{js_addr}')\">"
        f"{ICON_SAVE}<span>연락처 저장하기</span></button>"
    ) if is_active else ""

    action_guide = (
        "<p class=\"action-guide\">진료 문의 및 예약은 위 버튼을 이용하세요.</p>"
        if is_active
        else ""
    )

    value_section = (
        "<section class=\"card value-card\">"
        "<h2 class=\"section-title\">세종시 치과의사회가 보증하는 가치</h2>"
        "<ul class=\"value-list\">"
        "<li class=\"value-item\">"
        f"<div class=\"value-icon-box\">{ICON_CHECK}</div>"
        "<div class=\"value-text\">"
        "<strong class=\"value-head\">윤리 진료 준수</strong>"
        "<span class=\"value-desc\">원칙을 지키는 책임 진료</span>"
        "</div>"
        "</li>"
        "<li class=\"value-item\">"
        f"<div class=\"value-icon-box\">{ICON_CHECK}</div>"
        "<div class=\"value-text\">"
        "<strong class=\"value-head\">지속적인 학술 활동</strong>"
        "<span class=\"value-desc\">정기 학술대회 및 최신 임상 교육 이수</span>"
        "</div>"
        "</li>"
        "<li class=\"value-item\">"
        f"<div class=\"value-icon-box\">{ICON_CHECK}</div>"
        "<div class=\"value-text\">"
        "<strong class=\"value-head\">지역사회 공헌</strong>"
        "<span class=\"value-desc\">시민 구강검진, 취약계층 봉사활동 참여</span>"
        "</div>"
        "</li>"
        "</ul>"
        "</section>"
    ) if is_active else ""

    extra_payload = _load_clinic_extra(clinic_id)
    chatbot_html = ""
    if extra_payload:
        extra_json = _serialize_extra_json(extra_payload)
        chatbot_html = _render_chatbot_widget(extra_json, tel_href, map_href)

    body = (
        f"<div class=\"page-container\" data-page-type=\"clinic\" data-clinic-id=\"{safe_clinic_id_attr}\">"
        "<header class=\"section-brand\">"
        f"<h1 class=\"clinic-title\">{safe_name}</h1>"
        "<div class=\"brand-meta\">"
        f"<span class=\"badge {badge_class}\">{safe_badge}</span>"
        f"{seal_html}"
        "</div>"
        "</header>"
        "<section class=\"section-action\">"
        f"{cta_row}"
        f"{save_contact_btn}"
        f"{action_guide}"
        "</section>"
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
        f"{value_section}"
        "<footer class=\"section-footer\">"
        "<div class=\"official-logos\">"
        f"<img class=\"logo-grayscale\" src=\"{sejong_logo}\" alt=\"세종시치과의사회\">"
        f"<img class=\"logo-grayscale\" src=\"{kda_logo}\" alt=\"대한치과의사협회\">"
        "</div>"
        "<p class=\"footer-msg\">본 페이지는 <strong>세종특별자치시 치과의사회</strong>가<br>공식 정보를 보증하는 의료기관 안내입니다.</p>"
        "<div class=\"footer-meta\">"
        f"<span>인증기간: {safe_validity}</span>"
        f"<span>Updated: {safe_updated}</span>"
        "</div>"
        f"{_render_external_links()}"
        "</footer>"
        f"{chatbot_html}"
        "</div>"
    )
    return _render_page(cfg, title=safe_name, body=body)


def _load_clinic_extra(clinic_id: str) -> dict[str, object] | None:
    extra_path = _CLINIC_EXTRA_DIR / f"{clinic_id}.json"
    if not extra_path.exists():
        return None

    raw = extra_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:  # noqa: PERF203
        raise ValueError(f"Invalid clinic_extra JSON: {extra_path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"clinic_extra must be a JSON object: {extra_path}")
    return data


def _serialize_extra_json(data: dict[str, object]) -> str:
    json_text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return json_text.replace("<", "\\u003c")


def _render_chatbot_widget(extra_json: str, tel_href: str, map_href: str) -> str:
    cta_links = ""
    if tel_href:
        cta_links += f"<a href=\"{tel_href}\" class=\"chat-cta-btn\">전화상담</a>"
    if map_href:
        cta_links += f"<a href=\"{map_href}\" class=\"chat-cta-btn\" target=\"_blank\" rel=\"noopener noreferrer\">지도보기</a>"
    cta_html = f"<div class=\"chat-cta\">{cta_links}</div>" if cta_links else ""

    return (
        f"<script type=\"application/json\" id=\"clinic-extra-json\">{extra_json}</script>"
        "<div class=\"chat-widget\" id=\"chat-widget\">"
        "<button class=\"chat-fab\" type=\"button\" aria-label=\"문의하기\">문의하기</button>"
        "<div class=\"chat-panel\" role=\"dialog\" aria-hidden=\"true\">"
        "<div class=\"chat-header\">"
        "<div class=\"chat-title\">치과 안내 챗봇</div>"
        "<button class=\"chat-close\" type=\"button\" aria-label=\"닫기\">×</button>"
        "</div>"
        "<div class=\"chat-disclaimer\">개인정보/증상은 입력하지 마세요. 진료 상담은 전화로 안내합니다.</div>"
        "<div class=\"chat-body\" id=\"chat-body\" aria-live=\"polite\"></div>"
        "<div class=\"chat-quick\">"
        "<button type=\"button\" data-quick=\"hours\">진료시간</button>"
        "<button type=\"button\" data-quick=\"parking\">주차</button>"
        "<button type=\"button\" data-quick=\"reservation\">예약</button>"
        "<button type=\"button\" data-quick=\"directions\">오시는 길</button>"
        "</div>"
        "<div class=\"chat-input\">"
        "<input type=\"text\" placeholder=\"예: 주차 가능해요? / 진료시간 알려줘\">"
        "<button type=\"button\" class=\"chat-send\">전송</button>"
        "</div>"
        f"{cta_html}"
        "</div>"
        "</div>"
        "<script>"
        "(function(){"
        "var extraEl=document.getElementById('clinic-extra-json');"
        "var widget=document.getElementById('chat-widget');"
        "if(!extraEl||!widget){return;}"
        "var extra;try{extra=JSON.parse(extraEl.textContent||'{}');}catch(e){return;}"
        "var panel=widget.querySelector('.chat-panel');"
        "var fab=widget.querySelector('.chat-fab');"
        "var closeBtn=widget.querySelector('.chat-close');"
        "var body=widget.querySelector('.chat-body');"
        "var input=widget.querySelector('.chat-input input');"
        "var sendBtn=widget.querySelector('.chat-send');"
        "function addMessage(text, who){"
        "var bubble=document.createElement('div');"
        "bubble.className='chat-bubble '+who;"
        "bubble.textContent=text;"
        "body.appendChild(bubble);"
        "body.scrollTop=body.scrollHeight;"
        "}"
        "function ensureIntro(){"
        "if(body.getAttribute('data-init')){return;}"
        "addMessage('안내 가능한 항목: 진료시간/주차/예약/오시는 길', 'bot');"
        "body.setAttribute('data-init','1');"
        "}"
        "function toggle(open){"
        "if(open){widget.classList.add('open');panel.setAttribute('aria-hidden','false');ensureIntro();input.focus();}"
        "else{widget.classList.remove('open');panel.setAttribute('aria-hidden','true');}"
        "}"
        "fab.addEventListener('click', function(){toggle(!widget.classList.contains('open'));});"
        "closeBtn.addEventListener('click', function(){toggle(false);});"
        "function normalize(text){return (text||'').toLowerCase().replace(/[\\s\\p{P}\\p{S}]/gu,'');}"
        "var medicalKeywords=['아파','통증','염증','피','부음','고름','시림','충치','임플란트','교정','신경치료','발치','사랑니','약','처방','진단','치료','비용','가격','얼마','보험','실비','CT','엑스레이'];"
        "function containsMedical(text){return medicalKeywords.some(function(k){return text.indexOf(k)!==-1;});}"
        "function containsPersonal(text){"
        "if(/0\\d{1,2}[- ]?\\d{3,4}[- ]?\\d{4}/.test(text)){return true;}"
        "if(/\\S+@\\S+\\.\\S+/.test(text)){return true;}"
        "if(/\\d{6}[- ]?\\d{7}/.test(text)){return true;}"
        "return false;"
        "}"
        "function unknownMessage(){"
        "var msg=(extra.fallback&&extra.fallback.unknown)||'해당 문의는 페이지에 등록된 정보만으로는 확인이 어렵습니다.';"
        "if(msg.indexOf('전화')===-1||msg.indexOf('지도')===-1){msg+=' 전화상담 또는 지도보기 버튼을 이용해주세요.';}"
        "return msg;"
        "}"
        "function respond(text){addMessage(text,'bot');}"
        "function scoreFaq(input, faqQ){"
        "var inputN=normalize(input);"
        "var faqN=normalize(faqQ);"
        "if(!inputN||!faqN){return 0;}"
        "var score=0;"
        "if(inputN.indexOf(faqN)!==-1||faqN.indexOf(inputN)!==-1){score+=3;}"
        "var tokens=faqQ.split(/\\s+/).filter(function(t){return t.length>=2;});"
        "tokens.forEach(function(t){var tn=normalize(t);if(tn&&inputN.indexOf(tn)!==-1){score+=1;}});"
        "return score;"
        "}"
        "function handleQuestion(text){"
        "if(!text){return;}"
        "addMessage(text,'user');"
        "if(containsPersonal(text)){respond((extra.fallback&&extra.fallback.personal)||'개인정보는 입력하지 마세요. 전화로 문의해주세요.');return;}"
        "if(containsMedical(text)){respond((extra.fallback&&extra.fallback.medical)||'의학적 상담은 이 채널에서 안내할 수 없습니다. 전화로 문의해주세요.');return;}"
        "var quick=extra.quick_actions||{};"
        "if(text.indexOf('진료시간')!==-1||text.indexOf('시간')!==-1){if(quick.hours){respond(quick.hours);return;}}"
        "if(text.indexOf('주차')!==-1){if(quick.parking){respond(quick.parking);return;}}"
        "if(text.indexOf('예약')!==-1){if(quick.reservation){respond(quick.reservation);return;}}"
        "if(text.indexOf('오시는 길')!==-1||text.indexOf('위치')!==-1||text.indexOf('지도')!==-1){if(quick.directions){respond(quick.directions);return;}}"
        "var faqs=Array.isArray(extra.faq)?extra.faq:[];"
        "var best=null;var bestScore=0;"
        "faqs.forEach(function(item){"
        "var q=(item&&item.q)||'';var a=(item&&item.a)||'';"
        "var score=scoreFaq(text,q);"
        "if(score>bestScore){bestScore=score;best={a:a};}"
        "});"
        "if(best&&bestScore>=2&&best.a){respond(best.a);return;}"
        "respond(unknownMessage());"
        "}"
        "sendBtn.addEventListener('click', function(){"
        "var text=input.value.trim();"
        "input.value='';"
        "handleQuestion(text);"
        "});"
        "input.addEventListener('keydown', function(e){"
        "if(e.key==='Enter'){e.preventDefault();sendBtn.click();}"
        "});"
        "widget.querySelectorAll('[data-quick]').forEach(function(btn){"
        "btn.addEventListener('click', function(){"
        "var key=btn.getAttribute('data-quick');"
        "var quick=extra.quick_actions||{};"
        "var map={hours:quick.hours,parking:quick.parking,reservation:quick.reservation,directions:quick.directions};"
        "if(map[key]){respond(map[key]);}else{respond(unknownMessage());}"
        "});"
        "});"
        "})();"
        "</script>"
    )

def _render_page(cfg: AppConfig, title: str, body: str) -> str:
    safe_title = html.escape(title)
    robots = _render_robots(cfg.noindex)
    analytics = _render_analytics(cfg)

    vcard_script = (
        "<script>"
        "function saveContact(name, phone, address) {"
        "  var vcard = 'BEGIN:VCARD\\nVERSION:3.0\\nFN:' + name + '\\nTEL;TYPE=CELL:' + phone + '\\nADR;TYPE=WORK:;;' + address + ';;;\\nEND:VCARD';"
        "  var blob = new Blob([vcard], { type: 'text/vcard' });"
        "  var url = URL.createObjectURL(blob);"
        "  var a = document.createElement('a');"
        "  a.style.display = 'none';"
        "  a.href = url;"
        "  a.download = name + '.vcf';"
        "  document.body.appendChild(a);"
        "  a.click();"
        "  document.body.removeChild(a);"
        "  window.URL.revokeObjectURL(url);"
        "}"
        "</script>"
    )

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
        "--btn-soft-bg:#eff6ff;--btn-soft-text:#1e40af;"
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
        ".cta-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}"
        ".cta-row > .btn:first-child{grid-column:span 2}"
        ".btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:16px;border-radius:12px;font-weight:700;font-size:1rem;border:none;cursor:pointer;position:relative;overflow:hidden;transition:all 0.1s}"
        ".btn:active{transform:scale(0.98);opacity:0.9}"
        ".btn-primary{background:var(--primary);color:white;box-shadow:0 4px 10px rgba(23, 37, 84, 0.25)}"
        ".btn-secondary{background:#fff;color:var(--text-main);border:1px solid #cbd5e1;box-shadow:var(--shadow-card)}"
        ".btn-soft{background:var(--btn-soft-bg);color:var(--btn-soft-text);border:1px solid transparent}"
        ".btn-soft:hover{background:#dbeafe}"
        ".btn-full{width:100%;margin-top:4px}"
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
        ".footer-msg{font-size:0.75rem;color:var(--text-light);margin-bottom:20px;line-height:1.5}"
        ".footer-msg strong{color:var(--text-sub);font-weight:600}"
        ".footer-meta{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;font-size:0.7rem;color:var(--text-light);margin-bottom:28px}"
        ".link-list{display:flex;justify-content:center;gap:14px}"
        ".link-item a{font-size:0.75rem;color:var(--text-sub);font-weight:600;text-decoration:underline;text-decoration-color:#cbd5e1}"
        ".link-url{display:none}"
        ".empty-state{text-align:center;padding:60px 20px}"
        ".icon-area{font-size:2.5rem;font-weight:900;color:#e2e8f0;margin-bottom:20px}"
        ".chat-widget{position:fixed;right:16px;bottom:16px;z-index:9999;font-size:14px}"
        ".chat-fab{height:56px;padding:0 18px;border-radius:28px;background:var(--primary);color:#fff;border:none;font-weight:700;box-shadow:0 8px 16px rgba(15,23,42,0.2)}"
        ".chat-panel{position:fixed;right:16px;bottom:84px;width:min(420px,calc(100vw - 32px));background:#fff;border:1px solid #e2e8f0;border-radius:16px;box-shadow:0 12px 24px rgba(15,23,42,0.18);display:none;flex-direction:column;overflow:hidden}"
        ".chat-widget.open .chat-panel{display:flex}"
        ".chat-header{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:#f8fafc;border-bottom:1px solid #e2e8f0}"
        ".chat-title{font-weight:700;font-size:0.95rem;color:var(--text-main)}"
        ".chat-close{border:none;background:transparent;font-size:20px;line-height:1;color:var(--text-light);cursor:pointer}"
        ".chat-disclaimer{padding:8px 16px;font-size:0.75rem;color:var(--text-light);border-bottom:1px dashed #e2e8f0;background:#f8fafc}"
        ".chat-body{padding:14px 16px;max-height:240px;overflow:auto;display:flex;flex-direction:column;gap:10px}"
        ".chat-bubble{padding:10px 12px;border-radius:12px;font-size:0.85rem;line-height:1.4;max-width:85%}"
        ".chat-bubble.bot{background:#f1f5f9;color:var(--text-main);align-self:flex-start;border:1px solid #e2e8f0}"
        ".chat-bubble.user{background:#172554;color:#fff;align-self:flex-end}"
        ".chat-quick{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;padding:0 16px 12px}"
        ".chat-quick button{border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:8px 6px;font-size:0.8rem;font-weight:600;color:var(--text-main)}"
        ".chat-input{display:flex;gap:8px;padding:0 16px 14px}"
        ".chat-input input{flex:1;border:1px solid #cbd5e1;border-radius:10px;padding:10px;font-size:0.85rem}"
        ".chat-send{border:none;background:var(--primary);color:#fff;border-radius:10px;padding:0 14px;font-weight:700}"
        ".chat-cta{display:flex;gap:8px;padding:0 16px 16px}"
        ".chat-cta-btn{flex:1;text-align:center;padding:10px;border-radius:10px;background:#f8fafc;border:1px solid #e2e8f0;font-size:0.8rem;font-weight:600;color:var(--text-sub)}"
        ".chat-cta-btn:first-child{background:#172554;color:#fff;border-color:#172554}"
        "@media (max-width:340px){.cta-row{grid-template-columns:1fr}.cta-row > .btn:first-child{grid-column:auto}}"
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
        f"{vcard_script}"
        "</head>"
        "<body>"
        "<main class=\"wrap\">"
        f"{body}"
        "</main>"
        "</body>"
        "</html>"
    )


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
        "var container=document.querySelector('[data-page-type=\\\"clinic\\\"]');"
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
