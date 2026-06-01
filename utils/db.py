import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def get_connection(dbname: str | None = None):
    password = os.getenv("PGPASSWORD")
    if not password:
        raise ValueError(
            "PGPASSWORD nije postavljen. "
            "Napravi .env iz .env.example (cp .env.example .env) ili postavi env var: "
            "macOS/Linux: export PGPASSWORD='...' | "
            "Windows: $env:PGPASSWORD='...' - vidi README.md"
        )

    database = dbname or os.getenv("PGDATABASE", "ecommerce_bronze")

    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=database,
        user=os.getenv("PGUSER", "postgres"),
        password=password,
    )


if __name__ == "__main__":
    conn = get_connection()
    print("Konekcija uspjela!")
    conn.close()
