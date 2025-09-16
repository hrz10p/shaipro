import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values


CLIENTS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS clients (
    client_code INTEGER PRIMARY KEY,
    IIN TEXT,
    phoneNum TEXT,
    name TEXT,
    status TEXT,
    age INTEGER,
    city TEXT,
    avg_monthly_balance_KZT NUMERIC
);
"""

TRANSACTIONS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS transactions (
    client_code INTEGER,
    name TEXT,
    product TEXT,
    status TEXT,
    city TEXT,
    date DATE,
    category TEXT,
    amount NUMERIC,
    currency TEXT
);
"""

TRANSFERS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS transfers (
    client_code INTEGER,
    name TEXT,
    product TEXT,
    status TEXT,
    city TEXT,
    date DATE,
    type TEXT,
    direction TEXT,
    amount NUMERIC,
    currency TEXT
);
"""

def create_postgres_connection():
    load_dotenv('.env')
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    dbname = os.getenv('DB_NAME')
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )
    return conn


def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute(CLIENTS_TABLE_DDL)
        cur.execute(TRANSACTIONS_TABLE_DDL)
        cur.execute(TRANSFERS_TABLE_DDL)
    conn.commit()


def truncate_tables(conn):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE clients")
        cur.execute("TRUNCATE TABLE transactions")
        cur.execute("TRUNCATE TABLE transfers")
    conn.commit()


def copy_csv_into_table(conn, table_name: str, csv_path: str):
    with open(csv_path, 'r', encoding='utf-8') as f, conn.cursor() as cur:
        cur.copy_expert(f"COPY {table_name} FROM STDIN WITH (FORMAT csv, HEADER true)", f)
    conn.commit()


def load_all():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')
    clients_csv = os.path.join(data_dir, 'clients_enriched.csv')
    transactions_csv = os.path.join(data_dir, 'transactions_all.csv')
    transfers_csv = os.path.join(data_dir, 'transfers_all.csv')

    if not os.path.exists(clients_csv):
        raise FileNotFoundError(clients_csv)
    if not os.path.exists(transactions_csv):
        raise FileNotFoundError(transactions_csv)
    if not os.path.exists(transfers_csv):
        raise FileNotFoundError(transfers_csv)

    conn = create_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET client_encoding TO 'UTF8'")

        create_tables(conn)
        truncate_tables(conn)

        copy_csv_into_table(conn, 'clients', clients_csv)
        copy_csv_into_table(conn, 'transactions', transactions_csv)
        copy_csv_into_table(conn, 'transfers', transfers_csv)
    finally:
        conn.close()


if __name__ == '__main__':
    load_all()