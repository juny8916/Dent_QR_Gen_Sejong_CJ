"""Create a sample Excel file for local testing."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    data = {
        "치과명": [
            "세종스마일치과",
            "세종행복치과",
            "세종바른치과",
        ],
        "주소": [
            "세종시 나성로 123",
            "세종시 도움1로 45",
            "세종시 새롬로 78",
        ],
        "전화": [
            "044-123-4567",
            "044-234-5678",
            "044-345-6789",
        ],
        "대표원장": [
            "김세종",
            "이행복",
            "박바른",
        ],
        "홈페이지": [
            "https://example.com",
            "sejong-happy.co.kr",
            "",
        ],
    }
    df = pd.DataFrame(data)
    output_path = Path("data") / "clinics.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    print(f"Created sample Excel at {output_path}")


if __name__ == "__main__":
    main()
