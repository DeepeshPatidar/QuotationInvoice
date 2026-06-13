#!/usr/bin/env python3
"""Verify the layered application before packaging."""

import os
import subprocess
import sys
import tempfile


def run_check(label, code):
    print(f"\n{label}...")
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=".",
    )
    if result.returncode == 0:
        print(result.stdout.strip() or "   OK")
        return True
    print(result.stderr.strip())
    return False


def test_app():
    checks = [
        (
            "1. Checking Python syntax",
            """
import compileall
assert compileall.compile_file("Quote.py", quiet=1)
assert compileall.compile_dir("app", quiet=1)
print("   Syntax OK")
""",
        ),
        (
            "2. Checking layered imports",
            """
from Quote import CustomersTab, InvoicesTab, ItemsTab, ProformaInvoiceTab, QuotationsTab
from app.database import Database
from app.main import create_window
from app.pdf import DocumentGenerator, ProformaDocumentGenerator
from app.services import InvoiceService, QuotationService, TaxService
print("   Layered imports successful")
""",
        ),
        (
            "3. Checking database migrations",
            f"""
from app.database import Database
db = Database({os.path.join(tempfile.gettempdir(), "apex_prebuild_test.db")!r})
assert db.conn.execute("PRAGMA user_version").fetchone()[0] >= 1
db.conn.close()
print("   Database initialized")
""",
        ),
        (
            "4. Checking financial calculations",
            """
from app.services import TaxService
result = TaxService().calculate(
    [{"description": "Test", "qty": 2, "unit_price": "100"}],
    tax_percent=18,
    discount_percent=10,
)
assert str(result.total) == "212.40"
print("   Financial calculations successful")
""",
        ),
    ]
    return all(run_check(label, code) for label, code in checks)


if __name__ == "__main__":
    print("=" * 60)
    print(" APEX QUOTATION MANAGER - PRE-BUILD TEST")
    print("=" * 60)
    raise SystemExit(0 if test_app() else 1)
