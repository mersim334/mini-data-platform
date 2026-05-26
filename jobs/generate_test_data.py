"""
Generise ~10_000 redova po CSV fajlu.
Otprilike svaki 50. red (50, 100, 150, ...) je namjerno los.
Pokretanje: python jobs/generate_test_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

ROW_COUNT = 10_000
BAD_EVERY = 50
random.seed(42)

FIRST_NAMES = ["Amir", "Lejla", "Marko", "Sara", "Nedim", "Emina", "Ivan", "Adnan", "Amna", "Haris"]
LAST_NAMES = ["Hadzic", "Mujic", "Petrovic", "Kovacevic", "Basic", "Horvat", "Catic", "Delic", "Salihovic"]
COUNTRIES = ["Bosna i Hercegovina", "Srbija", "Hrvatska", "bih"]
PRODUCT_NAMES = [
    "Slusalice", "Zvucnik", "Blender", "Stolica", "Lampa", "Sto", "Kabel",
    "Monitor", "Tipkovnica", "Mis", "Webcam", "Router", "Tablet", "Telefon",
]
CATEGORIES = ["Elektronika", "Namjestaj", "Oprema", "Accesoires"]
CARRIERS = ["DHL", "Posta BH", "FedEx", "GLS"]
ORDER_STATUSES = ["completed", "pending", "cancelled", "shipped", "refunded"]
PAYMENT_STATUSES = ["success", "failed", "pending", "refunded"]
SHIPMENT_STATUSES = ["delivered", "in_transit", "returned", "pending", "cancelled"]
PAYMENT_METHODS = ["credit_card", "paypal", "bank_transfer"]


def d(start: date, offset: int) -> str:
    return (start + timedelta(days=offset % 365)).isoformat()


def write_csv(name: str, header: list[str], rows: list[dict]) -> None:
    path = DATA_DIR / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"OK {name}: {len(rows)} redova")


def bad_slot(i: int) -> bool:
    return i % BAD_EVERY == 0


def generate_customers() -> None:
    start = date(2023, 1, 1)
    rows = []
    for i in range(1, ROW_COUNT + 1):
        row = {
            "customer_id": str(i),
            "first_name": random.choice(FIRST_NAMES),
            "last_name": random.choice(LAST_NAMES),
            "email": f"user{i}@example.com",
            "country": random.choice(COUNTRIES),
            "created_at": d(start, i),
            "customer_type": "individual",
        }

        if bad_slot(i):
            err = (i // BAD_EVERY) % 8
            if err == 0:
                row["email"] = f"user{i}@example.com"  # duplikat sa i-50
                if i > BAD_EVERY:
                    row["email"] = f"user{i - BAD_EVERY}@example.com"
            elif err == 1:
                row["email"] = ""
            elif err == 2:
                row["first_name"] = str(i)
            elif err == 3:
                row["first_name"] = f"Firma {i} d.o.o."
                row["customer_type"] = "individual"
            elif err == 4:
                row["first_name"] = f"Partner {i} d.o.o."
                row["last_name"] = ""
                row["customer_type"] = "company"
            elif err == 5:
                row["country"] = ""
            elif err == 6:
                row["email"] = f"los-email-{i}"
            elif err == 7:
                row["first_name"] = ""

        rows.append(row)

    write_csv(
        "customers.csv",
        ["customer_id", "first_name", "last_name", "email", "country", "created_at", "customer_type"],
        rows,
    )


def generate_products() -> None:
    start = date(2023, 1, 1)
    rows = []
    for i in range(1, ROW_COUNT + 1):
        row = {
            "product_id": str(i),
            "product_name": f"{random.choice(PRODUCT_NAMES)} {i}",
            "category": random.choice(CATEGORIES),
            "price": f"{random.uniform(5, 500):.2f}",
            "created_at": d(start, i % 300),
        }

        if bad_slot(i):
            err = (i // BAD_EVERY) % 5
            if err == 0:
                row["price"] = "-10.00"
            elif err == 1:
                row["price"] = "0.00"
            elif err == 2:
                row["product_name"] = ""
            elif err == 3:
                row["category"] = ""
            elif err == 4 and i > BAD_EVERY:
                row["product_id"] = str(i - BAD_EVERY)

        rows.append(row)

    write_csv(
        "products.csv",
        ["product_id", "product_name", "category", "price", "created_at"],
        rows,
    )


def generate_orders() -> None:
    start = date(2024, 1, 1)
    rows = []
    for i in range(1, ROW_COUNT + 1):
        qty = random.randint(1, 5)
        price = random.uniform(10, 300)
        row = {
            "order_id": str(1000 + i),
            "customer_id": str((i % ROW_COUNT) + 1),
            "product_id": str((i % 500) + 1),
            "quantity": str(qty),
            "order_amount": f"{qty * price:.2f}",
            "order_date": d(start, i % 200),
            "status": random.choice(ORDER_STATUSES),
        }

        if bad_slot(i):
            err = (i // BAD_EVERY) % 7
            if err == 0:
                row["quantity"] = "0"
            elif err == 1:
                row["quantity"] = "-2"
            elif err == 2:
                row["order_amount"] = "-50.00"
            elif err == 3:
                row["customer_id"] = "999999"
            elif err == 4:
                row["product_id"] = "999999"
            elif err == 5:
                row["status"] = "INVALID_STATUS"
            elif err == 6:
                row["status"] = ""

        rows.append(row)

    write_csv(
        "orders.csv",
        ["order_id", "customer_id", "product_id", "quantity", "order_amount", "order_date", "status"],
        rows,
    )


def generate_payments() -> None:
    start = date(2024, 1, 1)
    rows = []
    for i in range(1, ROW_COUNT + 1):
        row = {
            "payment_id": str(5000 + i),
            "order_id": str(1000 + i),
            "payment_method": random.choice(PAYMENT_METHODS),
            "amount": f"{random.uniform(10, 1000):.2f}",
            "payment_date": d(start, i % 200),
            "status": random.choice(PAYMENT_STATUSES),
        }

        if bad_slot(i):
            err = (i // BAD_EVERY) % 5
            if err == 0:
                row["amount"] = "-1.00"
            elif err == 1:
                row["order_id"] = "999999"
            elif err == 2:
                row["payment_method"] = ""
            elif err == 3:
                row["status"] = "BAD_STATUS"
            elif err == 4:
                row["amount"] = "0.00"

        rows.append(row)

    write_csv(
        "payments.csv",
        ["payment_id", "order_id", "payment_method", "amount", "payment_date", "status"],
        rows,
    )


def generate_shipments() -> None:
    start = date(2024, 1, 1)
    rows = []
    for i in range(1, ROW_COUNT + 1):
        ship = d(start, i % 200)
        delivery = d(start, (i % 200) + 3)
        row = {
            "shipment_id": str(7000 + i),
            "order_id": str(1000 + i),
            "carrier": random.choice(CARRIERS),
            "tracking_number": f"BA{i:09d}",
            "ship_date": ship,
            "delivery_date": delivery,
            "status": random.choice(SHIPMENT_STATUSES),
        }

        if bad_slot(i):
            err = (i // BAD_EVERY) % 5
            if err == 0:
                row["order_id"] = "999999"
            elif err == 1:
                row["status"] = "UNKNOWN"
            elif err == 2:
                row["tracking_number"] = ""
                row["status"] = "delivered"
            elif err == 3:
                row["delivery_date"] = ship
                row["ship_date"] = delivery
            elif err == 4:
                row["carrier"] = ""

        rows.append(row)

    write_csv(
        "shipments.csv",
        [
            "shipment_id", "order_id", "carrier", "tracking_number",
            "ship_date", "delivery_date", "status",
        ],
        rows,
    )


def main() -> None:
    print(f"Generisanje {ROW_COUNT} redova, los red svakih {BAD_EVERY}...")
    generate_customers()
    generate_products()
    generate_orders()
    generate_payments()
    generate_shipments()
    print("Gotovo. Pokreni: python jobs/run_pipeline.py")


if __name__ == "__main__":
    main()
