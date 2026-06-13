import sqlite3

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add(self, customer: Customer) -> int:
        customer.validate()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO customers
                    (name, contact_person, phone, email, address, shipping_address, gstin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer.name.strip(),
                    customer.contact_person,
                    customer.phone,
                    customer.email,
                    customer.address,
                    customer.shipping_address,
                    customer.gstin,
                ),
            )
        return int(cursor.lastrowid)

    def get(self, customer_id: int) -> Customer | None:
        row = self.conn.execute(
            """
            SELECT id, name, contact_person, phone, email, address,
                   shipping_address, gstin
            FROM customers WHERE id = ?
            """,
            (customer_id,),
        ).fetchone()
        return Customer(*row[1:], id=row[0]) if row else None

    def update(self, customer: Customer) -> None:
        customer.validate()
        if customer.id is None:
            raise ValueError("Customer ID is required for update")
        with self.conn:
            self.conn.execute(
                """
                UPDATE customers
                SET name=?, contact_person=?, phone=?, email=?, address=?,
                    shipping_address=?, gstin=?
                WHERE id=?
                """,
                (
                    customer.name.strip(),
                    customer.contact_person,
                    customer.phone,
                    customer.email,
                    customer.address,
                    customer.shipping_address,
                    customer.gstin,
                    customer.id,
                ),
            )

    def delete(self, customer_id: int) -> None:
        references = self.conn.execute(
            """
            SELECT
                EXISTS(SELECT 1 FROM quotations WHERE customer_id=?),
                EXISTS(SELECT 1 FROM invoices WHERE customer_id=?),
                EXISTS(SELECT 1 FROM proforma_invoices WHERE customer_id=?)
            """,
            (customer_id, customer_id, customer_id),
        ).fetchone()
        if references and any(references):
            raise ValueError(
                "Customer cannot be deleted because documents reference it"
            )
        with self.conn:
            self.conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))

    def list_rows(self, keyword: str = "") -> list[tuple]:
        params: tuple[str, ...] = ()
        where = ""
        if keyword.strip():
            like = f"%{keyword.strip()}%"
            where = """
                WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                   OR contact_person LIKE ? OR gstin LIKE ?
            """
            params = (like, like, like, like, like)
        return self.conn.execute(
            f"""
            SELECT id, name, contact_person, phone, email, gstin, address,
                   shipping_address
            FROM customers
            {where}
            ORDER BY name
            """,
            params,
        ).fetchall()
