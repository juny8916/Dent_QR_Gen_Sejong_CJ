"""Module entry point for `python -m sejong_dental_qr`."""

from __future__ import annotations

from . import cli


def main() -> int:
    return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
