"""
quotation_tool.py

A simple quotation generator:
- stores customers, items and quotations in a local sqlite database (quotation.db)
- renders quotation, invoice and proforma LaTeX templates with Jinja2
- compiles generated .tex files to PDF using pdflatex
- saves outputs in quotations/, Proform/, and TaxInvoice/

Dependencies:
  pip install PyQt6 Jinja2 python-dateutil
  install MiKTeX or TeX Live and ensure pdflatex is on PATH
"""
import os
import shutil
import sqlite3
import subprocess
import json
from datetime import datetime
from dateutil import tz
from decimal import Decimal, ROUND_HALF_UP
from jinja2 import Environment, FileSystemLoader, TemplateError
import re

from PyQt6.QtWidgets import QMessageBox

DB_FILE = "quotation.db"
COMPANY_INFO_FILE = "company_info.json"
QUOTATION_FOLDER = "quotations"
PROFORMA_FOLDER = "Proform"
INVOICE_FOLDER = "TaxInvoice"
TEMPLATE_FOLDER = "templates"

# ---------- Utilities ----------
def money(value):
    """Return Decimal rounded to 2 decimals (string)"""
    v = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{v:.2f}"


def latex_escape(value):
    if value is None:
        return ""
    text = str(value)
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}'
    }
    for target, replacement in replacements.items():
        text = text.replace(target, replacement)
    return text


def latex_escape_term(value):
    """Escape term text for LaTeX while preserving common formatting commands."""
    if value is None:
        return ""
    term = str(value).strip()
    # Remove manual leading numbers like '1. ' or '2) ' so enumerate numbering stays clean.
    term = re.sub(r'^\s*\d+[\.)]\s*', '', term)
    # Also remove numbering inside a leading formatting command like '\textbf{10. ...}'.
    term = re.sub(r'^(\\[A-Za-z]+\{)\s*\d+[\.)]\s*', r'\1', term)
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}'
    }
    for target, replacement in replacements.items():
        term = term.replace(target, replacement)
    return term


def render_template(template_name, context, output_path):
    template_dir = os.path.join(os.path.dirname(__file__), TEMPLATE_FOLDER)
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    env.filters['latex_escape'] = latex_escape
    try:
        template = env.get_template(template_name)
    except TemplateError as e:
        raise RuntimeError(f"Unable to load LaTeX template '{template_name}': {e}")

    content = template.render(context)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def compile_tex(tex_path, output_dir):
    pdflatex = shutil.which('pdflatex')
    if not pdflatex:
        raise RuntimeError(
            'pdflatex not found. Install MiKTeX or TeX Live and ensure pdflatex is on PATH.'
        )

    result = subprocess.run(
        [pdflatex, '-interaction=nonstopmode', '-halt-on-error', '-output-directory', output_dir, tex_path],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"LaTeX compilation failed for {tex_path}: {result.stderr}\n{result.stdout}"
        )


def ensure_dirs():
    os.makedirs(QUOTATION_FOLDER, exist_ok=True)
    os.makedirs(PROFORMA_FOLDER, exist_ok=True)
    os.makedirs(INVOICE_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), TEMPLATE_FOLDER), exist_ok=True)

# ---------- Company Info Persistence ----------
def save_company_info(company_info):
    """Save company info to JSON file"""
    with open(COMPANY_INFO_FILE, 'w', encoding='utf-8') as f:
        json.dump(company_info, f, indent=2, ensure_ascii=False)

def load_company_info(default_company_info):
    """Load company info from JSON file, or return default if not found"""
    if os.path.exists(COMPANY_INFO_FILE):
        try:
            with open(COMPANY_INFO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default_company_info
    return default_company_info

# ---------- Database helper ----------
class Database:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()

        # customers
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            gstin TEXT
        )
        """)

        # Migration for customers table: add gstin column if missing
        cur.execute("PRAGMA table_info(customers)")
        columns = [row[1] for row in cur.fetchall()]
        if 'gstin' not in columns:
            print("INFO: Migrating customers table: adding 'gstin' column.")
            cur.execute("ALTER TABLE customers ADD COLUMN gstin TEXT")

        # items (catalog or ad-hoc)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            code TEXT,
            description TEXT NOT NULL,
            unit TEXT,
            unit_price REAL NOT NULL,
            sac_hsn TEXT
        )
        """)

        # quotations
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quotations (
            id INTEGER PRIMARY KEY,
            quote_no TEXT UNIQUE,
            customer_id INTEGER,
            quote_date TEXT,
            currency TEXT,
            subtotal REAL,
            tax_percent REAL,
            tax_amount REAL,
            total REAL,
            pdf_path TEXT,
            notes TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
        """)

        # quotation line items
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quotation_items (
            id INTEGER PRIMARY KEY,
            quotation_id INTEGER,
            item_description TEXT,
            item_code TEXT,
            qty REAL,
            unit TEXT,
            unit_price REAL,
            line_total REAL,
            sac_hsn TEXT,
            FOREIGN KEY(quotation_id) REFERENCES quotations(id)
        )
        """)

        # proforma invoices (generated from quotations)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS proforma_invoices (
            id INTEGER PRIMARY KEY,
            quotation_id INTEGER,
            proforma_no TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            proforma_date TEXT NOT NULL,
            currency TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax_percent REAL NOT NULL,
            tax_amount REAL NOT NULL,
            total REAL NOT NULL,
            pdf_path TEXT,
            notes TEXT,
            terms TEXT,
            status TEXT DEFAULT 'Draft', -- Draft, Issued, Accepted, Rejected
            advance_amount REAL DEFAULT 0,
            advance_date TEXT,
            created_from_quotation INTEGER, -- Reference to original quotation
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(quotation_id) REFERENCES quotations(id)
        )
        """)

        # Migration for proforma_invoices table: add terms column if missing
        cur.execute("PRAGMA table_info(proforma_invoices)")
        columns = [row[1] for row in cur.fetchall()]
        if 'terms' not in columns:
            print("INFO: Migrating proforma_invoices table: adding 'terms' column.")
            cur.execute("ALTER TABLE proforma_invoices ADD COLUMN terms TEXT")

        # proforma invoice line items
        cur.execute("""
        CREATE TABLE IF NOT EXISTS proforma_items (
            id INTEGER PRIMARY KEY,
            proforma_id INTEGER NOT NULL,
            item_description TEXT NOT NULL,
            item_code TEXT,
            qty REAL NOT NULL,
            unit TEXT,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            sac_hsn TEXT,
            FOREIGN KEY(proforma_id) REFERENCES proforma_invoices(id)
        )
        """)

        # invoices
        cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            quotation_id INTEGER,  -- Can be NULL if not based on a quote
            customer_id INTEGER NOT NULL,
            invoice_no TEXT UNIQUE NOT NULL,
            invoice_date TEXT NOT NULL,
            currency TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax_percent REAL NOT NULL,
            tax_amount REAL NOT NULL,
            total REAL NOT NULL,
            pdf_path TEXT,
            notes TEXT,
            version INTEGER DEFAULT 1,
            original_invoice_id INTEGER, -- Links to the original invoice if this is a new version
            status TEXT DEFAULT 'Draft', -- e.g., 'Draft', 'Issued', 'Paid', 'Cancelled'
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(quotation_id) REFERENCES quotations(id),
            FOREIGN KEY(original_invoice_id) REFERENCES invoices(id)
        )
        """)

        # invoice line items
        cur.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            item_description TEXT NOT NULL,
            item_code TEXT,
            qty REAL NOT NULL,
            unit TEXT,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            sac_hsn TEXT,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
        """)

        # Migration for quotations table: rename 'date' to 'quote_date' if it exists
        try:
            cur.execute("ALTER TABLE quotations RENAME COLUMN date TO quote_date")
            print("INFO: Migrated quotations table: renamed 'date' column to 'quote_date'.")
        except sqlite3.OperationalError:
            # This will fail if the column is already named 'quote_date' or doesn't exist, which is fine.
            pass

        # Migration for quotation_items table: add sac_hsn column if it doesn't exist
        cur.execute("PRAGMA table_info(quotation_items)")
        columns = [row[1] for row in cur.fetchall()]
        if 'sac_hsn' not in columns:
            print("INFO: Migrating quotation_items table: adding 'sac_hsn' column.")
            cur.execute("ALTER TABLE quotation_items ADD COLUMN sac_hsn TEXT")

        self.conn.commit()

    # ---------- Customer functions ----------
    def add_customer(self, name, contact_person="", phone="", email="", address="", gstin=""):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO customers (name, contact_person, phone, email, address, gstin) VALUES (?, ?, ?, ?, ?, ?)",
            (name, contact_person, phone, email, address, gstin)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_customer(self, customer_id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, contact_person, phone, email, address, gstin FROM customers WHERE id=?",
            (customer_id,)
        )
        r = cur.fetchone()
        if not r:
            return None
        keys = ["id", "name", "contact_person", "phone", "email", "address", "gstin"]
        return dict(zip(keys, r))

    def update_customer(self, customer_id, name, contact_person="", phone="", email="", address="", gstin=""):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE customers SET name=?, contact_person=?, phone=?, email=?, address=?, gstin=? WHERE id=?",
            (name, contact_person, phone, email, address, gstin, customer_id)
        )
        self.conn.commit()

    def get_all_customers(self):
        """Get all customers sorted by name"""
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, contact_person, phone, email, gstin, address FROM customers ORDER BY name")
        return cur.fetchall()

    def search_customers(self, keyword):
        """Search customers by name, phone, or email (case-insensitive)"""
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute("""
            SELECT id, name, contact_person, phone, email, gstin, address
            FROM customers
            WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? OR contact_person LIKE ? OR gstin LIKE ?
            ORDER BY name
        """, (like, like, like, like, like))
        return cur.fetchall()

    # ---------- Item functions ----------
    def _generate_item_code(self):
        cur = self.conn.cursor()
        cur.execute("SELECT code FROM items WHERE code LIKE 'APX%' ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
        if last and last[0].startswith("APX"):
            try:
                seq = int(last[0][3:]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"APX{seq:06d}"   # APX000001, APX000002, ...

    def add_item(self, description, unit, unit_price, sac_hsn=""):
        code = self._generate_item_code()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO items (code, description, unit, unit_price, sac_hsn) VALUES (?, ?, ?, ?, ?)""",
            (code, description, unit, unit_price, sac_hsn,)
        )
        self.conn.commit()
        return cur.lastrowid, code

    def get_item(self, item_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, code, description, unit, unit_price, sac_hsn FROM items WHERE id=?", (item_id,))
        return cur.fetchone()

    def get_items(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, code, description, unit, unit_price, sac_hsn FROM items ORDER BY description")
        return cur.fetchall()

    def search_items(self, keyword):
        """Search items by description or unit (case-insensitive)"""
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute("""
            SELECT id, code, description, unit, unit_price, sac_hsn
            FROM items
            WHERE description LIKE ? OR unit LIKE ?
            ORDER BY description
        """, (like, like))
        return cur.fetchall()

    def update_item(self, item_id, description, unit, unit_price, sac_hsn):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE items SET description=?, unit=?, unit_price=?, sac_hsn=? WHERE id=?",
            (description, unit, unit_price, sac_hsn, item_id)
        )
        self.conn.commit()


    def delete_item(self, item_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM items WHERE id=?", (item_id,))
        self.conn.commit()

    # ---------- Quotation functions ----------
    def save_quotation(self, quote_no, customer_id, date_iso, currency, subtotal,
                       tax_percent, tax_amount, total, pdf_path, notes, items):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO quotations (quote_no, customer_id, quote_date, currency, subtotal,
                                    tax_percent, tax_amount, total, pdf_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (quote_no, customer_id, date_iso, currency, subtotal, tax_percent,
              tax_amount, total, pdf_path, notes))
        qid = cur.lastrowid

        for it in items:
            cur.execute("""
                INSERT INTO quotation_items (quotation_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (qid, it['description'], it.get('item_code', ''),
                it['qty'], it.get('unit', ''), it['unit_price'], it['line_total'], it.get('sac_hsn', '')))

        self.conn.commit()
        return qid

    def last_quote_sequence_for_date(self, date_str_prefix):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT quote_no FROM quotations WHERE quote_no LIKE ? ORDER BY quote_no DESC LIMIT 1",
            (f"{date_str_prefix}%",)
        )
        r = cur.fetchone()
        return r[0] if r else None
    
    def get_quotation_details(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("SELECT customer_id, quote_date, notes FROM quotations WHERE id=?", (quotation_id,))
        r = cur.fetchone()
        if r:
            return {'customer_id': r[0], 'quote_date': r[1], 'notes': r[2]}
        return None

    def get_quotation_items(self, quotation_id):
        cur = self.conn.cursor()
        cur.execute("SELECT item_description, item_code, qty, unit, unit_price, sac_hsn FROM quotation_items WHERE quotation_id=?", (quotation_id,))
        return cur.fetchall()

    def get_all_quotations(self):
        """Get all quotations with customer names, sorted by date descending"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT q.id, q.quote_no, q.quote_date, c.name, q.total, 'Draft' as status
            FROM quotations q
            LEFT JOIN customers c ON q.customer_id = c.id
            ORDER BY q.quote_date DESC, q.quote_no DESC
        """)
        return cur.fetchall()

    def search_quotations(self, keyword):
        """Search quotations by quote number, customer name, or date"""
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute("""
            SELECT q.id, q.quote_no, q.quote_date, c.name, q.total, 'Draft' as status
            FROM quotations q
            LEFT JOIN customers c ON q.customer_id = c.id
            WHERE q.quote_no LIKE ? OR c.name LIKE ? OR q.quote_date LIKE ?
            ORDER BY q.quote_date DESC, q.quote_no DESC
        """, (like, like, like))
        return cur.fetchall()

    # ---------- Proforma Invoice functions ----------
    def create_proforma_from_quotation(self, quotation_id, proforma_no, proforma_date, notes=""):
        """Create a proforma invoice from an existing quotation"""
        cur = self.conn.cursor()

        # Get quotation details
        cur.execute("""
            SELECT customer_id, currency, subtotal, tax_percent, tax_amount, total, notes
            FROM quotations WHERE id=?
        """, (quotation_id,))
        quote = cur.fetchone()
        if not quote:
            raise ValueError("Quotation not found")

        customer_id, currency, subtotal, tax_percent, tax_amount, total, quote_notes = quote

        # Create proforma invoice
        cur.execute("""
            INSERT INTO proforma_invoices (
                quotation_id, proforma_no, customer_id, proforma_date, currency,
                subtotal, tax_percent, tax_amount, total, notes, terms, created_from_quotation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (quotation_id, proforma_no, customer_id, proforma_date, currency,
              subtotal, tax_percent, tax_amount, total, notes or quote_notes,
              "\n".join(default_proforma_terms()), quotation_id))

        proforma_id = cur.lastrowid

        # Copy quotation items to proforma items
        cur.execute("""
            INSERT INTO proforma_items (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
            SELECT ?, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn
            FROM quotation_items WHERE quotation_id=?
        """, (proforma_id, quotation_id))

        # Recalculate totals from copied proforma items to ensure consistency
        cur.execute("""
            SELECT SUM(line_total), SUM(qty * unit_price)
            FROM proforma_items WHERE proforma_id=?
        """, (proforma_id,))
        result = cur.fetchone()
        subtotal = result[0] if result and result[0] is not None else (result[1] or 0)
        tax_amount = (subtotal * tax_percent) / 100
        total = subtotal + tax_amount
        cur.execute("""
            UPDATE proforma_invoices
            SET subtotal=?, tax_amount=?, total=?
            WHERE id=?
        """, (subtotal, tax_amount, total, proforma_id))
        self.conn.commit()
        return proforma_id

    def get_proforma_details(self, proforma_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, quotation_id, proforma_no, customer_id, proforma_date, currency,
                   subtotal, tax_percent, tax_amount, total, pdf_path, notes, terms, status,
                   advance_amount, advance_date, created_from_quotation
            FROM proforma_invoices WHERE id=?
        """, (proforma_id,))
        r = cur.fetchone()
        if r:
            keys = ["id", "quotation_id", "proforma_no", "customer_id", "proforma_date", "currency",
                   "subtotal", "tax_percent", "tax_amount", "total", "pdf_path", "notes", "terms", "status",
                   "advance_amount", "advance_date", "created_from_quotation"]
            return dict(zip(keys, r))
        return None

    def get_proforma_items(self, proforma_id):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT item_description, item_code, qty, unit, unit_price, line_total, sac_hsn
            FROM proforma_items WHERE proforma_id=?
        """, (proforma_id,))
        return cur.fetchall()

    def update_proforma_item(self, proforma_id, item_index, item_description, item_code, qty, unit, unit_price, sac_hsn):
        """Update a specific item in proforma invoice"""
        cur = self.conn.cursor()

        # Get current items to find the one to update
        items = self.get_proforma_items(proforma_id)
        if item_index >= len(items):
            raise ValueError("Item index out of range")

        # Delete all items and re-insert (simpler than updating specific row)
        cur.execute("DELETE FROM proforma_items WHERE proforma_id=?", (proforma_id,))

        # Re-insert all items with the updated one
        for i, item in enumerate(items):
            if i == item_index:
                # Use the updated values
                line_total = qty * unit_price
                cur.execute("""
                    INSERT INTO proforma_items (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn))
            else:
                # Keep existing items
                desc, code, qty_val, unit_val, price, total, hsn = item
                cur.execute("""
                    INSERT INTO proforma_items (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (proforma_id, desc, code, qty_val, unit_val, price, total, hsn))

        self.conn.commit()

    def add_proforma_item(self, proforma_id, item_description, item_code, qty, unit, unit_price, sac_hsn):
        """Add a new item to proforma invoice"""
        line_total = qty * unit_price
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO proforma_items (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn))
        self.conn.commit()

    def delete_proforma_item(self, proforma_id, item_index):
        """Delete an item from proforma invoice"""
        cur = self.conn.cursor()

        # Get all items
        items = self.get_proforma_items(proforma_id)
        if item_index >= len(items):
            raise ValueError("Item index out of range")

        # Delete all and re-insert without the deleted one
        cur.execute("DELETE FROM proforma_items WHERE proforma_id=?", (proforma_id,))

        for i, item in enumerate(items):
            if i != item_index:
                desc, code, qty_val, unit_val, price, total, hsn = item
                cur.execute("""
                    INSERT INTO proforma_items (proforma_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (proforma_id, desc, code, qty_val, unit_val, price, total, hsn))

        self.conn.commit()

    def update_proforma_totals(self, proforma_id):
        """Recalculate and update proforma invoice totals"""
        cur = self.conn.cursor()

        # Calculate new totals from items
        cur.execute("""
            SELECT SUM(line_total), SUM(qty * unit_price)
            FROM proforma_items WHERE proforma_id=?
        """, (proforma_id,))
        result = cur.fetchone()
        if result:
            subtotal = result[0] if result[0] is not None else (result[1] or 0)

            # Get tax percent from proforma
            cur.execute("SELECT tax_percent FROM proforma_invoices WHERE id=?", (proforma_id,))
            tax_result = cur.fetchone()
            tax_percent = tax_result[0] if tax_result else 18.0

            tax_amount = (subtotal * tax_percent) / 100
            total = subtotal + tax_amount

            # Update proforma
            cur.execute("""
                UPDATE proforma_invoices
                SET subtotal=?, tax_amount=?, total=?
                WHERE id=?
            """, (subtotal, tax_amount, total, proforma_id))

        self.conn.commit()

    def get_all_proforma_invoices(self):
        """Get all proforma invoices with customer names"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, p.proforma_no, p.proforma_date, c.name, p.total, p.status
            FROM proforma_invoices p
            LEFT JOIN customers c ON p.customer_id = c.id
            ORDER BY p.proforma_date DESC, p.proforma_no DESC
        """)
        return cur.fetchall()

    def search_proforma_invoices(self, keyword):
        """Search proforma invoices by proforma number, customer name, or date"""
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute("""
            SELECT p.id, p.proforma_no, p.proforma_date, c.name, p.total, p.status
            FROM proforma_invoices p
            LEFT JOIN customers c ON p.customer_id = c.id
            WHERE p.proforma_no LIKE ? OR c.name LIKE ? OR p.proforma_date LIKE ?
            ORDER BY p.proforma_date DESC, p.proforma_no DESC
        """, (like, like, like))
        return cur.fetchall()

    def update_proforma_status(self, proforma_id, status, advance_amount=None, advance_date=None):
        """Update proforma invoice status and advance payment details"""
        cur = self.conn.cursor()
        if advance_amount is not None and advance_date is not None:
            cur.execute("""
                UPDATE proforma_invoices
                SET status=?, advance_amount=?, advance_date=?
                WHERE id=?
            """, (status, advance_amount, advance_date, proforma_id))
        else:
            cur.execute("""
                UPDATE proforma_invoices
                SET status=?
                WHERE id=?
            """, (status, proforma_id))
        self.conn.commit()

    def get_last_proforma_sequence_for_date(self, date_str_prefix):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT proforma_no FROM proforma_invoices WHERE proforma_no LIKE ? ORDER BY proforma_no DESC LIMIT 1",
            (f"{date_str_prefix}%",)
        )
        r = cur.fetchone()
        return r[0] if r else None

    # ---------- Invoice functions ----------
    def add_invoice(self, quotation_id, customer_id, invoice_no, invoice_date, currency,
                    subtotal, tax_percent, tax_amount, total, pdf_path, notes,
                    version=1, original_invoice_id=None, status='Draft'):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO invoices (quotation_id, customer_id, invoice_no, invoice_date, currency,
                                  subtotal, tax_percent, tax_amount, total, pdf_path, notes,
                                  version, original_invoice_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (quotation_id, customer_id, invoice_no, invoice_date, currency,
              subtotal, tax_percent, tax_amount, total, pdf_path, notes,
              version, original_invoice_id, status))
        self.conn.commit()
        return cur.lastrowid

    def update_invoice(self, invoice_id, quotation_id, customer_id, invoice_no, invoice_date, currency,
                       subtotal, tax_percent, tax_amount, total, pdf_path, notes,
                       version, original_invoice_id, status):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE invoices SET quotation_id=?, customer_id=?, invoice_no=?, invoice_date=?, currency=?,
                               subtotal=?, tax_percent=?, tax_amount=?, total=?, pdf_path=?, notes=?,
                               version=?, original_invoice_id=?, status=?
            WHERE id=?
        """, (quotation_id, customer_id, invoice_no, invoice_date, currency,
              subtotal, tax_percent, tax_amount, total, pdf_path, notes,
              version, original_invoice_id, status, invoice_id))
        self.conn.commit()

    def add_invoice_item(self, invoice_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO invoice_items (invoice_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (invoice_id, item_description, item_code, qty, unit, unit_price, line_total, sac_hsn))
        self.conn.commit()

    def delete_invoice_items(self, invoice_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        self.conn.commit()

    def get_invoice_details(self, invoice_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, quotation_id, customer_id, invoice_no, invoice_date, currency, subtotal, tax_percent, tax_amount, total, pdf_path, notes, version, original_invoice_id, status FROM invoices WHERE id=?", (invoice_id,))
        r = cur.fetchone()
        if r:
            keys = ["id", "quotation_id", "customer_id", "invoice_no", "invoice_date", "currency", "subtotal", "tax_percent", "tax_amount", "total", "pdf_path", "notes", "version", "original_invoice_id", "status"]
            return dict(zip(keys, r))
        return None

    def get_invoice_items(self, invoice_id):
        cur = self.conn.cursor()
        cur.execute("SELECT item_description, item_code, qty, unit, unit_price, line_total, sac_hsn FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        return cur.fetchall()

    def get_all_invoices(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, invoice_no, invoice_date, total, status FROM invoices ORDER BY invoice_date DESC, invoice_no DESC")
        return cur.fetchall()

    def search_invoices(self, keyword):
        """Search invoices by invoice number, customer name, date"""
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute("""
            SELECT i.id, i.invoice_no, i.invoice_date, i.total, i.status
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            WHERE i.invoice_no LIKE ? OR c.name LIKE ? OR i.invoice_date LIKE ?
            ORDER BY i.invoice_date DESC, i.invoice_no DESC
        """, (like, like, like))
        return cur.fetchall()

    def get_invoices_by_date_range(self, date_from, date_to):
        """Filter invoices by date range (YYYY-MM-DD format)"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, invoice_no, invoice_date, total, status
            FROM invoices
            WHERE invoice_date >= ? AND invoice_date <= ?
            ORDER BY invoice_date DESC, invoice_no DESC
        """, (date_from, date_to))
        return cur.fetchall()

    def get_invoices_by_status(self, status):
        """Filter invoices by status (Draft, Issued, Paid, etc.)"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, invoice_no, invoice_date, total, status
            FROM invoices
            WHERE status = ?
            ORDER BY invoice_date DESC, invoice_no DESC
        """, (status,))
        return cur.fetchall()

    def get_last_invoice_sequence_for_date(self, date_str_prefix):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT invoice_no FROM invoices WHERE invoice_no LIKE ? ORDER BY invoice_no DESC LIMIT 1",
            (f"{date_str_prefix}%",)
        )
        r = cur.fetchone()
        return r[0] if r else None


# ---------- PDF generator ----------
class QuotePDF:
    def __init__(self, company_info, terms=None, invoice_terms=None, logo_path=None):
        """
        company_info: dict with name, address, phone, email, gstin (optional)
        terms: list of terms strings for quotations
        invoice_terms: list of terms strings for invoices
        """
        self.company_info = company_info
        self.terms = terms or default_terms()
        self.invoice_terms = invoice_terms or default_invoice_terms()
        self.logo_path = logo_path

    def build(self, doc_type, doc_no, doc_date, customer, items, currency, subtotal, tax_percent, tax_amount, total, notes, output_path):
        ensure_dirs()

        template_name = 'invoice.tex.j2' if doc_type.lower() == 'invoice' else 'quotation.tex.j2'
        tex_path = os.path.splitext(output_path)[0] + '.tex'

        formatted_items = []
        for item in items:
            formatted_items.append({
                'description': latex_escape(item.get('description', '')),
                'code': latex_escape(item.get('code', item.get('item_code', ''))),
                'unit': latex_escape(item.get('unit', '')),
                'qty': money(item.get('qty', 0)),
                'unit_price': money(item.get('unit_price', 0)),
                'line_total': money(item.get('line_total', 0)),
                'sac_hsn': latex_escape(item.get('sac_hsn', ''))
            })

        context = {
            'company_info': {k: latex_escape(v) for k, v in self.company_info.items()},
            'doc_type': latex_escape(doc_type),
            'doc_no': latex_escape(doc_no),
            'doc_date': latex_escape(doc_date),
            'customer': {k: latex_escape(v) for k, v in customer.items()},
            'items': formatted_items,
            'currency': latex_escape(currency),
            'subtotal': money(subtotal),
            'tax_percent': money(tax_percent),
            'tax_amount': money(tax_amount),
            'total': money(total),
            'notes': latex_escape(notes),
            'terms': [latex_escape_term(term) for term in (self.invoice_terms if doc_type.lower() == 'invoice' else self.terms)],
            'logo_path': self.logo_path or ''
        }

        render_template(template_name, context, tex_path)
        compile_tex(tex_path, os.path.dirname(output_path))

# ---------- Defaults ----------
def default_terms():
    return [
        "This quotation is valid for 30 days from the date of issue.",
        "Prices are exclusive of applicable taxes unless otherwise specified.",
        "Delivery timeline will be confirmed after receipt of purchase order.",
        "50% advance with order, balance on delivery unless otherwise agreed.",
        "Warranty terms as per manufacturer's standard warranty unless specified."
    ]


def default_proforma_terms():
    return [
        "This proforma invoice is issued for advance payment confirmation.",
        "Goods/services supplied will be invoiced after payment confirmation.",
        "Prices are subject to final confirmation and applicable taxes.",
        "Delivery timeline will be finalized after receipt of advance payment.",
        "This document is computer-generated and does not require a physical signature."
    ]

def default_invoice_terms():
    return [
        "Payment is due within 30 days from the date of invoice.",
        "Late payments may incur interest at 2% per month.",
        "All disputes must be raised within 7 days of receipt of invoice.",
        "Goods once sold will not be taken back.",
        "This invoice is subject to local jurisdiction.",
        "GST and other applicable taxes as per government norms.",
        "Cheque payments should be made in favor of the company name.",
        "Bank details are provided for electronic transfers."
    ]

# ---------- Quote creation logic ----------
class QuotationService:
    def __init__(self, db: Database, pdf_maker: QuotePDF, currency="INR", tax_percent=18.0):
        self.db = db
        self.pdf_maker = pdf_maker
        self.currency = currency
        self.tax_percent = Decimal(str(tax_percent))

    def _generate_quote_no(self):
        # Q-YYYYMMDD-0001 (sequential per day)
        now = datetime.now(tz=tz.tzlocal())
        date_prefix = now.strftime("Q-%Y%m%d")
        last = self.db.last_quote_sequence_for_date(date_prefix)
        if last:
            # last like Q-20250918-0003
            try:
                seq = int(last.split('-')[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        return f"{date_prefix}-{seq:04d}"

    def create_quotation(self, customer_id, line_items, notes=""):
        """
        line_items: list of dicts: {description, qty, unit, unit_price}
        """
        customer = self.db.get_customer(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # compute lines
        items_processed = []
        subtotal = Decimal("0.00")
        for it in line_items:
            qty = Decimal(str(it.get('qty', 1)))
            up = Decimal(str(it.get('unit_price', 0)))
            line_total = (qty * up).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            items_processed.append({
                'description': it.get('description', ''),
                'code': it.get('item_code', ''),
                'qty': float(qty),
                'unit': it.get('unit', ''),
                'unit_price': float(up),
                'line_total': float(line_total),
                'sac_hsn': it.get('sac_hsn', '')
            })
            subtotal += line_total
        tax_percent_dec = Decimal(str(self.tax_percent))
        tax_amount = (subtotal * (tax_percent_dec / Decimal('100'))).quantize(Decimal("0.01"))
        total = (subtotal + tax_amount).quantize(Decimal("0.01"))

        #tax_amount = (subtotal * (self.tax_percent/Decimal('100'))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        #total = (subtotal + tax_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # create quote no and paths
        quote_no = self._generate_quote_no()
        quote_date = datetime.now(tz=tz.tzlocal()).strftime("%d %b %Y")
        ensure_dirs()
        filename = f"{quote_no}.pdf"
        pdf_path = os.path.join(QUOTATION_FOLDER, filename)

        # build pdf
        self.pdf_maker.build(
            doc_type="Quotation",
            doc_no=quote_no,
            doc_date=quote_date,
            customer=customer,
            items=items_processed,
            currency=self.currency,
            subtotal=float(subtotal),
            tax_percent=float(self.tax_percent),
            tax_amount=float(tax_amount),
            total=float(total),
            notes=notes,
            output_path=pdf_path
        )

        # save to db
        qid = self.db.save_quotation(
            quote_no=quote_no,
            customer_id=customer_id,
            date_iso=datetime.now(tz=tz.tzlocal()).isoformat(),
            currency=self.currency,
            subtotal=float(subtotal),
            tax_percent=float(self.tax_percent),
            tax_amount=float(tax_amount),
            total=float(total),
            pdf_path=pdf_path,
            notes=notes,
            items=items_processed
        )

        return {
            'quotation_id': qid,
            'quote_no': quote_no,
            'pdf_path': pdf_path,
            'subtotal': float(subtotal),
            'tax_amount': float(tax_amount),
            'total': float(total)
        }


# ---------- INVOICE SERVICE CLASS STARTS HERE ----------
class InvoiceService:
    def __init__(self, db: Database, pdf_maker: QuotePDF, currency="INR", tax_percent=18.0):
        self.db = db
        self.pdf_maker = pdf_maker
        self.currency = currency
        self.tax_percent = Decimal(str(tax_percent))

    def _generate_invoice_no(self):
        # INV-YYYYMMDD-0001 (sequential per day)
        now = datetime.now(tz=tz.tzlocal())
        date_prefix = now.strftime("INV-%Y%m%d")
        last = self.db.get_last_invoice_sequence_for_date(date_prefix)
        if last:
            try:
                seq = int(last.split('-')[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        return f"{date_prefix}-{seq:04d}"

    def calculate_totals(self, line_items):
        subtotal = Decimal("0.00")
        processed_items = []
        for it in line_items:
            qty = Decimal(str(it.get('qty', 1)))
            up = Decimal(str(it.get('unit_price', 0)))
            line_total = (qty * up).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            processed_items.append({
                'description': it.get('description', ''),
                'code': it.get('item_code', ''),
                'qty': float(qty),
                'unit': it.get('unit', ''),
                'unit_price': float(up),
                'line_total': float(line_total),
                'sac_hsn': it.get('sac_hsn', '')
            })
            subtotal += line_total
        tax_percent_dec = Decimal(str(self.tax_percent))
        tax_amount = (subtotal * (tax_percent_dec / Decimal('100'))).quantize(Decimal("0.01"))
        total = (subtotal + tax_amount).quantize(Decimal("0.01"))
        return processed_items, float(subtotal), float(tax_amount), float(total)

    def create_invoice(self, customer_id, line_items, notes="", quotation_id=None,
                       invoice_no=None, invoice_date=None, existing_invoice_id=None, status='Draft'):
        customer = self.db.get_customer(customer_id)
        if not customer:
            raise ValueError("Customer not found")

        processed_items, subtotal, tax_amount, total = self.calculate_totals(line_items)

        invoice_no = invoice_no if invoice_no else self._generate_invoice_no()
        invoice_date = invoice_date if invoice_date else datetime.now(tz=tz.tzlocal()).strftime("%d %b %Y")

        ensure_dirs()
        filename = f"{invoice_no}.pdf"
        pdf_path = os.path.join(INVOICE_FOLDER, filename)

        self.pdf_maker.build(
            doc_type="Invoice",
            doc_no=invoice_no,
            doc_date=invoice_date,
            customer=customer,
            items=processed_items,
            currency=self.currency,
            subtotal=subtotal,
            tax_percent=float(self.tax_percent),
            tax_amount=tax_amount,
            total=total,
            notes=notes,
            output_path=pdf_path
        )

        if existing_invoice_id:
            # Create a new version
            original_invoice_details = self.db.get_invoice_details(existing_invoice_id)
            new_version = original_invoice_details['version'] + 1 if original_invoice_details else 1
            invoice_id = self.db.add_invoice(
                quotation_id=quotation_id,
                customer_id=customer_id,
                invoice_no=f"{invoice_no}-v{new_version}", # Append version to invoice number
                invoice_date=invoice_date,
                currency=self.currency,
                subtotal=subtotal,
                tax_percent=float(self.tax_percent),
                tax_amount=tax_amount,
                total=total,
                pdf_path=pdf_path,
                notes=notes,
                version=new_version,
                original_invoice_id=existing_invoice_id,
                status=status
            )
        else:
            invoice_id = self.db.add_invoice(
                quotation_id=quotation_id,
                customer_id=customer_id,
                invoice_no=invoice_no,
                invoice_date=invoice_date,
                currency=self.currency,
                subtotal=subtotal,
                tax_percent=float(self.tax_percent),
                tax_amount=tax_amount,
                total=total,
                pdf_path=pdf_path,
                notes=notes,
                status=status
            )

        self.db.delete_invoice_items(invoice_id) # Clear old items if updating
        for item in processed_items:
            self.db.add_invoice_item(
                invoice_id=invoice_id,
                item_description=item['description'],
                item_code=item['code'],
                qty=item['qty'],
                unit=item['unit'],
                unit_price=item['unit_price'],
                line_total=item['line_total'],
                sac_hsn=item['sac_hsn']
            )

        return {
            'invoice_id': invoice_id,
            'invoice_no': invoice_no,
            'pdf_path': pdf_path,
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total': total
        }

# ---------- Proforma PDF Generator ----------
class ProformaPDF:
    def __init__(self, company_info, terms, logo_path=None):
        self.company_info = company_info
        self.terms = terms or default_proforma_terms()
        self.logo_path = logo_path

    def generate_pdf(self, proforma_no, proforma_date, customer, items, subtotal, tax_percent, tax_amount, total, currency="INR", notes=""):
        ensure_dirs()

        filename = f"PROFORMA_{proforma_no.replace('/', '_')}.pdf"
        pdf_path = os.path.join(PROFORMA_FOLDER, filename)
        tex_path = os.path.splitext(pdf_path)[0] + '.tex'

        formatted_items = []
        for item in items:
            desc, code, qty, unit, unit_price, line_total, hsn = item
            formatted_items.append({
                'description': latex_escape(desc),
                'code': latex_escape(code),
                'qty': money(qty),
                'unit': latex_escape(unit),
                'unit_price': money(unit_price),
                'line_total': money(line_total),
                'sac_hsn': latex_escape(hsn)
            })

        try:
            from num2words import num2words
            amount_words = num2words(int(total), lang='en_IN').title() + " Rupees Only"
        except Exception:
            amount_words = f"{latex_escape(currency)} {money(total)}"

        context = {
            'company_info': {k: latex_escape(v) for k, v in self.company_info.items()},
            'proforma_no': latex_escape(proforma_no),
            'proforma_date': latex_escape(proforma_date),
            'customer': {k: latex_escape(v) for k, v in customer.items()},
            'items': formatted_items,
            'currency': latex_escape(currency),
            'subtotal': money(subtotal),
            'tax_percent': money(tax_percent),
            'tax_amount': money(tax_amount),
            'total': money(total),
            'notes': latex_escape(notes),
            'terms': [latex_escape_term(term) for term in self.terms],
            'amount_words': amount_words,
            'logo_path': self.logo_path or ''
        }

        render_template('proforma.tex.j2', context, tex_path)
        compile_tex(tex_path, os.path.dirname(pdf_path))
        return pdf_path

# ---------- Example usage (for testing purposes) ----------
if __name__ == "__main__":
    # Example company info -- edit to your company details
    my_company = {
        'name': "ACME Instruments Pvt. Ltd.",
        'address': "123 Industrial Area,\nIndore, Madhya Pradesh\nIndia - 452001",
        'phone': "+91-731-XXXXXXX",
        'email': "sales@acmeinstruments.example",
        'gstin': "27XXXXXXXXX1Z5"
    }

    # Create DB and add a sample customer
    db = Database()
    # If you're running multiple times, this will create duplicate customers.
    # In real use you would add customers via a small UI or CLI and store their IDs.
    cust_id = db.add_customer(
        name="M/s. Example Customer",
        contact_person="Mr. Rajesh Kumar",
        phone="+91-98XXXXXXX",
        email="rajesh@example.com",
        address="10 Business Park,\nIndore, MP - 452010"
    )

    # Create PDF generator with default terms and optional logo (None)
    pdf_maker = QuotePDF(company_info=my_company, terms=None, logo_path=None)

    quotation_service = QuotationService(db=db, pdf_maker=pdf_maker, currency="INR", tax_percent=18.0)
    invoice_service = InvoiceService(db=db, pdf_maker=pdf_maker, currency="INR", tax_percent=18.0)

    # Example line items
    sample_items = [
        {'description': "Data acquisition module - imcCRONOSflex (expansion module)", 'qty': 1, 'unit': 'pcs', 'unit_price': 125000.00, 'sac_hsn': '90318000'},
        {'description': "Calibration & On-site integration", 'qty': 2, 'unit': 'days', 'unit_price': 7500.00},
        {'description': "Shipping & Handling", 'qty': 1, 'unit': 'lot', 'unit_price': 2500.00},
    ]

    notes = "Delivery: 4-6 weeks from receipt of P.O.\nPayment: 50% advance, balance before dispatch.\nValidity: 30 days."

    result = quotation_service.create_quotation(customer_id=cust_id, line_items=sample_items, notes=notes)
    
    print("Quotation created:")
    print("  Quote No:", result['quote_no'])
    print("  PDF saved at:", result['pdf_path'])
    print("  Subtotal:", money(result['subtotal']))
    print("  Tax:", money(result['tax_amount']))
    print("  Grand Total:", money(result['total']))
