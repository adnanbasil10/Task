"""
Database module: SQLite schema creation, CSV ingestion, and read-only query execution.
"""
import csv
import os
import re
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "supply_chain.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    segment TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    unit_price REAL,
    sku TEXT
);

CREATE TABLE IF NOT EXISTS addresses (
    id TEXT PRIMARY KEY,
    street TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT,
    status TEXT,
    total_amount REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER,
    unit_price REAL,
    total REAL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    address_id TEXT NOT NULL,
    delivery_date TEXT,
    status TEXT,
    tracking_number TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (address_id) REFERENCES addresses(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    invoice_date TEXT,
    due_date TEXT,
    status TEXT,
    total_amount REAL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    description TEXT,
    quantity INTEGER,
    unit_price REAL,
    total REAL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    payment_date TEXT,
    amount REAL,
    method TEXT,
    status TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Indexes on all foreign key columns
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_order_id ON deliveries(order_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_address_id ON deliveries(address_id);
CREATE INDEX IF NOT EXISTS idx_invoices_order_id ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
"""

# Tables and their CSV files (order matters for FK constraints)
TABLE_CSV_MAP = [
    ("customers", "customers.csv"),
    ("products", "products.csv"),
    ("addresses", "addresses.csv"),
    ("orders", "orders.csv"),
    ("order_items", "order_items.csv"),
    ("deliveries", "deliveries.csv"),
    ("invoices", "invoices.csv"),
    ("invoice_items", "invoice_items.csv"),
    ("payments", "payments.csv"),
]

# Dangerous SQL pattern for read-only enforcement
DANGEROUS_SQL_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|REINDEX|VACUUM|PRAGMA)",
    re.IGNORECASE
)


@contextmanager
def get_connection(readonly=False):
    """Context manager for database connections."""
    if readonly:
        uri = f"file:{DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def execute_readonly(sql: str, params: tuple = ()) -> list[dict]:
    """
    Execute a read-only SQL query. Rejects any write operations.
    Returns list of dicts.
    """
    # Enforce read-only at application level
    if DANGEROUS_SQL_PATTERN.match(sql.strip()):
        raise ValueError(f"Write operations are not allowed. Rejected: {sql[:80]}...")
    
    # Additional safety: reject multiple statements
    # Remove string literals and comments before checking for semicolons
    cleaned = re.sub(r"'[^']*'", "", sql)
    cleaned = re.sub(r"--.*$", "", cleaned, flags=re.MULTILINE)
    if cleaned.strip().rstrip(";").count(";") > 0:
        raise ValueError("Multiple SQL statements are not allowed.")
    
    with get_connection(readonly=True) as conn:
        cursor = conn.execute(sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def get_schema_ddl() -> str:
    """Return the full schema DDL for LLM prompting."""
    return SCHEMA_SQL


def get_sample_rows(table: str, limit: int = 3) -> list[dict]:
    """Get sample rows from a table for LLM prompting."""
    return execute_readonly(f"SELECT * FROM {table} LIMIT ?", (limit,))


def get_table_count(table: str) -> int:
    """Get row count for a table."""
    result = execute_readonly(f"SELECT COUNT(*) as cnt FROM {table}")
    return result[0]["cnt"] if result else 0


def get_all_table_counts() -> dict:
    """Get row counts for all tables."""
    counts = {}
    for table, _ in TABLE_CSV_MAP:
        counts[table] = get_table_count(table)
    return counts


def load_csv_to_table(conn, table_name: str, csv_filename: str):
    """Load a CSV file into a database table."""
    csv_path = os.path.join(DATA_DIR, csv_filename)
    if not os.path.exists(csv_path):
        print(f"  ⚠ CSV not found: {csv_path}")
        return 0
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return 0
        
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        for row in rows:
            values = [row[col] for col in columns]
            conn.execute(sql, values)
    
    return len(rows)


def init_db(force_reload: bool = False):
    """
    Initialize the database: create schema and load CSV data.
    Returns dict of table counts.
    """
    db_exists = os.path.exists(DB_PATH)
    
    if db_exists and not force_reload:
        print("📊 Database already exists. Skipping CSV ingestion.")
        return get_all_table_counts()
    
    if db_exists and force_reload:
        os.remove(DB_PATH)
        print("🗑️ Removed existing database for reload.")
    
    print("🔧 Creating database schema...")
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        
        print("📥 Loading CSV data...")
        total = 0
        for table, csv_file in TABLE_CSV_MAP:
            count = load_csv_to_table(conn, table, csv_file)
            print(f"   ✓ {table}: {count} records")
            total += count
        
        conn.commit()
        print(f"✅ Total records loaded: {total}")
    
    return get_all_table_counts()
