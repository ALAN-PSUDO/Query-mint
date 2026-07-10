"""Seed the query-mint PostgreSQL database with realistic relational data."""

from __future__ import annotations

import os
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


load_dotenv()


DB_URL = (
	os.getenv("DB_URL")
	or os.getenv("DATABASE_URL")
	or os.getenv("NEON_DATABASE_URL")
	or "USER:PASSWORD@HOST:5432/DB_NAME"
)

RANDOM_SEED = 42
USER_COUNT = 60
PRODUCT_COUNT = 60
ORDER_COUNT = 150

FIRST_NAMES = [
	"Ava",
	"Mia",
	"Noah",
	"Emma",
	"Liam",
	"Olivia",
	"Elijah",
	"Sophia",
	"Lucas",
	"Isabella",
	"Mason",
	"Amelia",
	"Ethan",
	"Harper",
	"Logan",
	"Evelyn",
	"James",
	"Abigail",
	"Benjamin",
	"Emily",
]

LAST_NAMES = [
	"Carter",
	"Brooks",
	"Mitchell",
	"Turner",
	"Morgan",
	"Parker",
	"Reed",
	"Hayes",
	"Coleman",
	"Price",
	"Bennett",
	"Ward",
	"Foster",
	"Howard",
	"Ross",
	"Murphy",
	"Cooper",
	"Bailey",
	"Rivera",
	"Gray",
]

DEPARTMENTS = [
	"Sales",
	"Marketing",
	"Engineering",
	"Finance",
	"Operations",
	"Human Resources",
	"Customer Success",
	"Product",
]

PRODUCT_ADJECTIVES = [
	"Adaptive",
	"Advanced",
	"Apex",
	"Bright",
	"Core",
	"Dynamic",
	"Elite",
	"Essential",
	"Fusion",
	"Global",
	"Insight",
	"Latitude",
	"Nimbus",
	"Nova",
	"Prime",
	"Quantum",
	"Summit",
	"Vertex",
]

PRODUCT_NOUNS = [
	"Analytics Suite",
	"Notebook",
	"Workstation",
	"Headset",
	"Router",
	"Monitor",
	"Keyboard",
	"Mouse",
	"Dock",
	"Projector",
	"Camera",
	"Speaker",
	"Planner",
	"Chair",
	"Tablet",
	"Hub",
	"Scanner",
	"Storage Drive",
]

CATEGORIES = [
	"Electronics",
	"Office Supplies",
	"Furniture",
	"Accessories",
	"Software",
	"Networking",
]


def money(value: float | Decimal) -> Decimal:
	return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_users() -> list[tuple[str, str, str, date]]:
	users: list[tuple[str, str, str, date]] = []
	used_emails: set[str] = set()
	base_hire_date = date(2016, 1, 4)

	for index in range(USER_COUNT):
		first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
		last_name = LAST_NAMES[(index * 3) % len(LAST_NAMES)]
		name = f"{first_name} {last_name}"
		department = random.choice(DEPARTMENTS)
		hire_offset = random.randint(0, 9 * 365)
		hire_date = base_hire_date + timedelta(days=hire_offset)

		email_local = f"{first_name.lower()}.{last_name.lower()}"
		if email_local in used_emails:
			email_local = f"{email_local}{index + 1}"
		used_emails.add(email_local)
		email = f"{email_local}@querymint.test"

		users.append((name, email, department, hire_date))

	return users


def generate_products() -> list[tuple[str, str, Decimal, int]]:
	products: list[tuple[str, str, Decimal, int]] = []

	for index in range(PRODUCT_COUNT):
		adjective = PRODUCT_ADJECTIVES[index % len(PRODUCT_ADJECTIVES)]
		noun = PRODUCT_NOUNS[(index * 2) % len(PRODUCT_NOUNS)]
		category = random.choice(CATEGORIES)
		price = money(random.uniform(24.0, 950.0))
		stock_quantity = random.randint(20, 500)
		products.append((f"{adjective} {noun}", category, price, stock_quantity))

	return products


def generate_orders(users: list[tuple[str, str, str, date]], products: list[tuple[str, str, Decimal, int]]) -> list[tuple[int, int, date, Decimal]]:
	orders: list[tuple[int, int, date, Decimal]] = []
	today = date.today()
	start_date = today - timedelta(days=730)

	for _ in range(ORDER_COUNT):
		user_id = random.randint(1, len(users))
		product_id = random.randint(1, len(products))
		_, _, price, _ = products[product_id - 1]
		quantity = random.randint(1, 5)
		order_total = money(price * quantity)
		order_date = start_date + timedelta(days=random.randint(0, 730))
		orders.append((user_id, product_id, order_date, order_total))

	return orders


def create_schema(connection) -> None:
	ddl = """
	DROP TABLE IF EXISTS orders CASCADE;
	DROP TABLE IF EXISTS products CASCADE;
	DROP TABLE IF EXISTS users CASCADE;

	CREATE TABLE users (
		user_id SERIAL PRIMARY KEY,
		name VARCHAR(150) NOT NULL,
		email VARCHAR(255) NOT NULL UNIQUE,
		department VARCHAR(100) NOT NULL,
		hire_date DATE NOT NULL
	);

	CREATE TABLE products (
		product_id SERIAL PRIMARY KEY,
		name VARCHAR(200) NOT NULL,
		category VARCHAR(100) NOT NULL,
		price DECIMAL(10, 2) NOT NULL,
		stock_quantity INT NOT NULL
	);

	CREATE TABLE orders (
		order_id SERIAL PRIMARY KEY,
		user_id INT NOT NULL REFERENCES users(user_id),
		product_id INT NOT NULL REFERENCES products(product_id),
		order_date DATE NOT NULL,
		order_total DECIMAL(10, 2) NOT NULL
	);
	"""

	with connection.cursor() as cursor:
		cursor.execute(ddl)
	connection.commit()


def seed_data(connection) -> None:
	random.seed(RANDOM_SEED)

	users = generate_users()
	products = generate_products()
	orders = generate_orders(users, products)

	with connection.cursor() as cursor:
		execute_values(
			cursor,
			"INSERT INTO users (name, email, department, hire_date) VALUES %s",
			users,
		)
		execute_values(
			cursor,
			"INSERT INTO products (name, category, price, stock_quantity) VALUES %s",
			products,
		)
		execute_values(
			cursor,
			"INSERT INTO orders (user_id, product_id, order_date, order_total) VALUES %s",
			orders,
		)

	connection.commit()


def main() -> None:
	if "USER:PASSWORD@HOST:5432/DB_NAME" in DB_URL:
		print("Set DB_URL, DATABASE_URL, or NEON_DATABASE_URL before running seed.py.")
		raise SystemExit(1)

	with psycopg2.connect(DB_URL) as connection:
		create_schema(connection)
		seed_data(connection)

	print("Database seeded successfully with Users, Products, and Orders!")


if __name__ == "__main__":
	main()
