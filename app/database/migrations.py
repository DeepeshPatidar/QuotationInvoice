"""Small, ordered SQLite migrations.

The legacy schema creation remains compatible while new upgrades are applied
through SQLite's user_version value.
"""

import sqlite3
from collections.abc import Callable

Migration = Callable[[sqlite3.Connection], None]


def _migration_1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_quotations_customer_id
            ON quotations(customer_id);
        CREATE INDEX IF NOT EXISTS idx_quotations_quote_date
            ON quotations(quote_date);
        CREATE INDEX IF NOT EXISTS idx_invoices_customer_id
            ON invoices(customer_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date
            ON invoices(invoice_date);
        CREATE INDEX IF NOT EXISTS idx_proforma_customer_id
            ON proforma_invoices(customer_id);
        """
    )


def _migration_2(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_sequences (
            financial_year TEXT PRIMARY KEY,
            last_sequence INTEGER NOT NULL DEFAULT 0
        )
        """
    )


MIGRATIONS: tuple[Migration, ...] = (_migration_1, _migration_2)


def run_migrations(conn: sqlite3.Connection) -> None:
    current_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    for version, migration in enumerate(MIGRATIONS, start=1):
        if version <= current_version:
            continue
        with conn:
            migration(conn)
            conn.execute(f"PRAGMA user_version = {version}")
