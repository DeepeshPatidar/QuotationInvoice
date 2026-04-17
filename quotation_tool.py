"""
quotation_tool.py

A simple quotation generator:
- stores customers, items and quotations in a local sqlite database (quotation.db)
- generates a PDF quotation using reportlab and saves it to quotations/
- example usage at bottom demonstrates adding a customer, items and creating a quote

Dependencies:
  pip install reportlab python-dateutil
"""

import os
import sqlite3
from datetime import datetime
from dateutil import tz
from decimal import Decimal, ROUND_HALF_UP
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

from PyQt6.QtWidgets import QMessageBox

DB_FILE = "quotation.db"
PDF_FOLDER = "quotations"

# ---------- Utilities ----------
def money(value):
    """Return Decimal rounded to 2 decimals (string)"""
    v = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{v:.2f}"

def ensure_dirs():
    os.makedirs(PDF_FOLDER, exist_ok=True)

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
            address TEXT
        )
        """)

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
    def add_customer(self, name, contact_person="", phone="", email="", address=""):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO customers (name, contact_person, phone, email, address) VALUES (?, ?, ?, ?, ?)",
            (name, contact_person, phone, email, address)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_customer(self, customer_id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, contact_person, phone, email, address FROM customers WHERE id=?",
            (customer_id,)
        )
        r = cur.fetchone()
        if not r:
            return None
        keys = ["id", "name", "contact_person", "phone", "email", "address"]
        return dict(zip(keys, r))

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
    def __init__(self, company_info, terms=None, logo_path=None):
        """
        company_info: dict with name, address, phone, email, gstin (optional)
        terms: list of terms strings
        """
        #logo_path = r'D:\ApexAutomobileTesting\Offer\PythonApp\DSUB9PIN.png'
       
        self.company_info = company_info
        self.terms = terms or default_terms()
        self.logo_path = logo_path
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
        self.styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))

    def build(self, doc_type, doc_no, doc_date, customer, items, currency, subtotal, tax_percent, tax_amount, total, notes, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
        flow = []

        # Header - company name & logo
        header_table_data = []
        left = []
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                im = Image(self.logo_path, width=50*mm, height=20*mm)
                left.append(im)
            except Exception:
                left.append(Paragraph(self.company_info.get('name', ''), self.styles['Title']))
        else:
            left.append(Paragraph(f"<b>{self.company_info.get('name','')}</b>", self.styles['Title']))

        left.append(Paragraph(self.company_info.get('address', '').replace('\n', '<br/>'), self.styles['Normal']))
        left.append(Paragraph(f"Phone: {self.company_info.get('phone','')} | Email: {self.company_info.get('email','')}", self.styles['Normal']))
        if self.company_info.get('gstin'):
            left.append(Paragraph(f"GSTIN: {self.company_info.get('gstin')}", self.styles['Normal']))

        right = []
        right.append(Paragraph(f"<b>{doc_type}</b>", self.styles['Heading2']))
        right.append(Spacer(1, 6))
        right.append(Paragraph(f"<b>{doc_type} No:</b> {doc_no}", self.styles['Normal']))
        right.append(Paragraph(f"<b>Date:</b> {doc_date}", self.styles['Normal']))

        header_table_data = [[left, right]]
        header_table = Table(header_table_data, colWidths=[110*mm, 60*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        flow.append(header_table)
        flow.append(Spacer(1, 8))

        # Customer details
        cust_text = f"""<b>To:</b><br/>{customer.get('name','')}<br/>{customer.get('contact_person','')}<br/>{customer.get('address','')}<br/>Phone: {customer.get('phone','')}<br/>Email: {customer.get('email','')}"""
        flow.append(Paragraph(cust_text, self.styles['Normal']))
        flow.append(Spacer(1, 8))

        # Items Table
        table_data = [
            ["S.No", "Description", "Item Code", "Unit", "Quantity", "Rate ("+currency+")", "Line Total ("+currency+")"]
        ]
        for i, it in enumerate(items, start=1):
            table_data.append([
                str(i),
                Paragraph(it['description'], self.styles['Normal']),
                it.get('code', ''),
                it.get('unit', ''),
                money(it['qty']),
                money(it['unit_price']),
                money(it['line_total'])
            ])


        # totals rows appended
       

        table_data.append(["", "", "", "", Paragraph("Subtotal:", self.styles['Normal']), Paragraph(money(subtotal), self.styles['Normal'])])
        table_data.append(["", "", "", "", Paragraph(f"Tax ({money(tax_percent)}%):", self.styles['Normal']), Paragraph(money(tax_amount), self.styles['Normal'])])
        table_data.append(["", "", "", "", Paragraph("<b>Total:</b>", self.styles['Normal']), Paragraph(f"<b>{money(total)}</b>", self.styles['Normal'])])


        col_widths = [15*mm, 60*mm, 25*mm, 20*mm, 20*mm, 25*mm, 30*mm]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)

        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-4), 0.25, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (2,1), (2,-1), 'CENTER'),
            ('ALIGN', (4,1), (5,-1), 'RIGHT'),
            ('SPAN', (0,-3), (3,-3)),
            ('SPAN', (0,-2), (3,-2)),
            ('SPAN', (0,-1), (3,-1)),
            ('LINEABOVE', (4,-1), (5,-1), 1, colors.black)
        ]))
        flow.append(t)
        flow.append(Spacer(1, 12))

        # Notes
        if notes:
            flow.append(Paragraph("<b>Notes:</b>", self.styles['Normal']))
            flow.append(Paragraph(notes.replace('\n','<br/>'), self.styles['Normal']))
            flow.append(Spacer(1, 8))

        # Terms
        flow.append(Paragraph("<b>Terms & Conditions:</b>", self.styles['Normal']))
        for idx, term in enumerate(self.terms, start=1):
            flow.append(Paragraph(f"{idx}. {term}", self.styles['Normal']))

        flow.append(Spacer(1, 16))
        # Signature placeholder
        signature_table = Table([
            ["", "For " + self.company_info.get('name', '' )],
            ["", ""],
            ["", "_______________________"],
            ["", "Authorized Signatory"]
        ], colWidths=[100*mm, 60*mm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('TOPPADDING', (0,0), (-1,-1), 6)
        ]))
        flow.append(signature_table)

        # Build
        doc.build(flow)

# ---------- Defaults ----------
def default_terms():
    return [
        "This quotation is valid for 30 days from the date of issue.",
        "Prices are exclusive of applicable taxes unless otherwise specified.",
        "Delivery timeline will be confirmed after receipt of purchase order.",
        "50% advance with order, balance on delivery unless otherwise agreed.",
        "Warranty terms as per manufacturer's standard warranty unless specified."
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
        pdf_path = os.path.join(PDF_FOLDER, filename)

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
            quote_date=datetime.now(tz=tz.tzlocal()).isoformat(),
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
        pdf_path = os.path.join(PDF_FOLDER, filename)

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

    result = service.create_quotation(customer_id=cust_id, line_items=sample_items, notes=notes)
    
    print("Quotation created:")
    print("  Quote No:", result['quote_no'])
    print("  PDF saved at:", result['pdf_path'])
    print("  Subtotal:", money(result['subtotal']))
    print("  Tax:", money(result['tax_amount']))
    print("  Grand Total:", money(result['total']))
