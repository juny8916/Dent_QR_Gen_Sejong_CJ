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
        ]
    }
    df = pd.DataFrame(data)
    output_path = Path("data") / "clinics.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    print(f"Created sample Excel at {output_path}")


if __name__ == "__main__":
    main()
