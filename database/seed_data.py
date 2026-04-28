from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.mock_data import seed_database_if_needed  # noqa: E402


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/metrics")
    fixed_today = os.getenv("FIXED_TODAY")
    if fixed_today:
        from datetime import date

        today = date.fromisoformat(fixed_today)
    else:
        from datetime import date

        today = date.today()

    engine = create_engine(database_url, future=True)
    total_rows = seed_database_if_needed(engine, today)
    with engine.connect() as connection:
        maximum_date = connection.execute(text("SELECT MAX(statistics_date) FROM fact_delivery_orders")).scalar_one()
        record_count = connection.execute(text("SELECT COUNT(*) FROM fact_delivery_orders")).scalar_one()

    print(
        f"Seed complete. inserted_or_existing={total_rows}, table_count={record_count}, max_statistics_date={maximum_date}"
    )


if __name__ == "__main__":
    main()

