"""QR code generation helpers."""

from __future__ import annotations

from pathlib import Path

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
