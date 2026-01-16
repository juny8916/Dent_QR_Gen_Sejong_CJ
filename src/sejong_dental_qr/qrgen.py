"""
QR 이미지 생성 모듈.

- 무엇(What): 치과별 URL을 QR로 생성하고, 필요 시 캡션(치과명)을 붙인 named 버전을 만든다.
- 왜(Why): 환자가 QR을 스캔해 정적 페이지(docs/c/<clinic_id>/)로 이동하도록 하기 위함.
- 어떻게(How): qrcode + PIL로 PNG를 생성하며, 오류정정/크기/폰트는 config로 제어한다.
"""

from __future__ import annotations

from pathlib import Path
import logging

from PIL import Image, ImageDraw, ImageFont
import qrcode


# QR 오류정정 레벨 매핑(표준 규칙, 변경 시 기존 QR 품질에 영향).
_EC_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


# -----------------------------------------------------------------------------
# [WHY] 치과별 랜딩 URL을 QR로 제공하여 환자 접근성을 높인다.
# [WHAT] url → output/qr/<clinic_id>.png 생성.
# [HOW] 오류정정(ec), box_size, border는 config 값 사용.
# -----------------------------------------------------------------------------
def make_qr_png(
    url: str,
    out_path: str | Path,
    ec: str,
    box_size: int,
    border: int,
) -> None:
    ec_value = _EC_MAP.get(str(ec).upper())
    if ec_value is None:
        raise ValueError(f"Invalid QR error correction: {ec}")

    qr = qrcode.QRCode(
        error_correction=ec_value,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    output_path = Path(out_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def find_noto_cjk_font() -> Path:
    candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    search_roots = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
    patterns = [
        "NotoSansCJK*.ttc",
        "NotoSansCJK*.otf",
        "NotoSansCJK*.ttf",
        "NotoSerifCJK*.ttc",
        "NotoSerifCJK*.otf",
        "NotoSerifCJK*.ttf",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            matches = sorted(root.rglob(pattern))
            if matches:
                return matches[0]

    logging.error(
        "Noto CJK font not found. Install with: sudo apt install -y fonts-noto-cjk"
    )
    raise RuntimeError("Noto CJK font not found")


# -----------------------------------------------------------------------------
# [WHY] 운영자가 치과명 캡션이 포함된 QR을 별도로 전달할 수 있게 한다.
# [WHAT] output/qr/<clinic_id>_named.png 생성(QR 위 + 캡션 아래).
# [HOW] QR 크기는 유지하고, 캔버스를 아래로 확장하여 텍스트 영역을 추가한다.
# -----------------------------------------------------------------------------
def make_qr_named_png(
    qr_png_path: Path,
    clinic_name: str,
    out_path: Path,
    font_path: str | None,
    font_size: int,
) -> None:
    qr_image = Image.open(qr_png_path).convert("RGB")
    qr_width, qr_height = qr_image.size

    font_file = Path(font_path) if font_path and font_path.strip() else find_noto_cjk_font()
    if not font_file.exists():
        raise ValueError(f"Font not found: {font_file}")

    padding_x = max(12, int(qr_width * 0.06))
    max_width = qr_width - (padding_x * 2)
    font, lines, used_size, fits = _fit_caption_text(
        clinic_name,
        font_file,
        font_size,
        max_width,
    )
    if not fits:
        logging.warning(
            "Caption text may overflow at minimum font size (%s).",
            used_size,
        )

    line_height = _text_height(font)
    line_spacing = max(4, int(used_size * 0.2))
    padding_y = max(10, int(used_size * 0.4))
    caption_height = padding_y * 2 + line_height * len(lines) + line_spacing * (len(lines) - 1)

    output_image = Image.new("RGB", (qr_width, qr_height + caption_height), "white")
    output_image.paste(qr_image, (0, 0))

    draw = ImageDraw.Draw(output_image)
    y = qr_height + padding_y
    for line in lines:
        line_width = _text_width(line, font)
        x = max(0, (qr_width - line_width) // 2)
        draw.text((x, y), line, fill="black", font=font)
        y += line_height + line_spacing

    out_path.parent.mkdir(parents=True, exist_ok=True)
    output_image.save(out_path)


def _fit_caption_text(
    text: str,
    font_path: Path,
    font_size: int,
    max_width: int,
) -> tuple[ImageFont.FreeTypeFont, list[str], int, bool]:
    min_size = 16
    size = font_size
    while size >= min_size:
        font = ImageFont.truetype(str(font_path), size)
        lines, fits = _wrap_text(text, font, max_width)
        if fits:
            return font, lines, size, True
        size -= 1

    font = ImageFont.truetype(str(font_path), min_size)
    lines, fits = _wrap_text(text, font, max_width)
    return font, lines, min_size, fits


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> tuple[list[str], bool]:
    if not text:
        return [""], True
    if " " in text:
        return _wrap_words(text, font, max_width)
    return _wrap_chars(text, font, max_width)


def _wrap_words(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> tuple[list[str], bool]:
    words = text.split(" ")
    if any(_text_width(word, font) > max_width for word in words if word):
        return _wrap_chars(text, font, max_width)

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _text_width(candidate, font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == 2:
                return lines, False
    if current:
        lines.append(current)
    return lines, True


def _wrap_chars(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> tuple[list[str], bool]:
    lines: list[str] = []
    current = ""
    for ch in text:
        if not current and ch == " ":
            continue
        candidate = current + ch
        if _text_width(candidate, font) <= max_width or not current:
            current = candidate
            continue
        lines.append(current)
        current = ch
        if len(lines) == 2:
            return lines, False
    if current:
        lines.append(current)
    return lines, True


def _text_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    if not text:
        return 0
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def _text_height(font: ImageFont.FreeTypeFont) -> int:
    bbox = font.getbbox("Ag")
    return bbox[3] - bbox[1]
