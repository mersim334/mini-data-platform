import os

import psycopg2


def get_connection(dbname: str | None = None):
    password = os.getenv("PGPASSWORD")
    if not password:
        raise ValueError(
            "PGPASSWORD nije postavljen. "
            "U PowerShellu: $env:PGPASSWORD='tvoja_lozinka'"
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
