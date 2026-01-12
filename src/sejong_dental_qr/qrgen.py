"""QR code generation helpers."""

from __future__ import annotations

from pathlib import Path
import logging

from PIL import Image, ImageDraw, ImageFont
import qrcode


_EC_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


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
