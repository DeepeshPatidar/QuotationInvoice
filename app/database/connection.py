from quotation_tool import Database as LegacyDatabase

from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository

from .migrations import run_migrations


class Database(LegacyDatabase):
    """Compatibility facade backed by focused repositories."""

    def __init__(self, db_file="quotation.db"):
        super().__init__(db_file)
        self.conn.execute("PRAGMA foreign_keys = ON")
        run_migrations(self.conn)
        self.customers = CustomerRepository(self.conn)
        self.invoices = InvoiceRepository(self.conn)

    def add_customer(
        self,
        name,
        contact_person="",
        phone="",
        email="",
        address="",
        shipping_address="",
        gstin="",
    ):
        return self.customers.add(
            Customer(
                name=name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                shipping_address=shipping_address,
                gstin=gstin,
            )
        )

    def get_customer(self, customer_id):
        customer = self.customers.get(customer_id)
        if customer is None:
            return None
        return {
            "id": customer.id,
            "name": customer.name,
            "contact_person": customer.contact_person,
            "phone": customer.phone,
            "email": customer.email,
            "address": customer.address,
            "shipping_address": customer.shipping_address,
            "gstin": customer.gstin,
        }

    def update_customer(
        self,
        customer_id,
        name,
        contact_person="",
        phone="",
        email="",
        address="",
        shipping_address="",
        gstin="",
    ):
        self.customers.update(
            Customer(
                id=customer_id,
                name=name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                shipping_address=shipping_address,
                gstin=gstin,
            )
        )

    def delete_customer(self, customer_id):
        self.customers.delete(customer_id)

    def get_all_customers(self):
        return self.customers.list_rows()

    def search_customers(self, keyword):
        return self.customers.list_rows(keyword)

    def get_customer_choices(self):
        return self.conn.execute(
            "SELECT id, name FROM customers ORDER BY name"
        ).fetchall()

    def get_quotation_choices(self):
        return self.conn.execute(
            "SELECT id, quote_no FROM quotations ORDER BY quote_no DESC"
        ).fetchall()

    def get_quotation_pdf_path(self, quotation_id):
        row = self.conn.execute(
            "SELECT pdf_path FROM quotations WHERE id=?", (quotation_id,)
        ).fetchone()
        return row[0] if row else None

    def delete_quotation(self, quotation_id):
        with self.conn:
            self.conn.execute(
                "DELETE FROM quotation_items WHERE quotation_id=?", (quotation_id,)
            )
            self.conn.execute("DELETE FROM quotations WHERE id=?", (quotation_id,))

    def update_proforma_pdf_path(self, proforma_id, pdf_path):
        with self.conn:
            self.conn.execute(
                "UPDATE proforma_invoices SET pdf_path=? WHERE id=?",
                (pdf_path, proforma_id),
            )

    def save_proforma_changes(
        self,
        proforma_id,
        items,
        notes,
        terms,
        subtotal,
        tax_amount,
        total,
    ):
        with self.conn:
            self.conn.execute(
                "DELETE FROM proforma_items WHERE proforma_id=?", (proforma_id,)
            )
            self.conn.executemany(
                """
                INSERT INTO proforma_items
                    (proforma_id, item_description, item_code, qty, unit,
                     unit_price, line_total, sac_hsn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (proforma_id, desc, code, qty, unit, price, line_total, hsn)
                    for desc, code, qty, unit, price, line_total, hsn in items
                ),
            )
            self.conn.execute(
                """
                UPDATE proforma_invoices
                SET notes=?, terms=?, subtotal=?, tax_amount=?, total=?
                WHERE id=?
                """,
                (notes, terms, subtotal, tax_amount, total, proforma_id),
            )

    def get_invoice_details(self, invoice_id):
        return self.invoices.get(invoice_id)

    def get_all_invoices(self):
        return self.invoices.list_rows()

    def search_invoices(self, keyword):
        return self.invoices.list_rows(keyword=keyword)

    def get_invoices_by_status(self, status):
        return self.invoices.list_rows(status=status)
