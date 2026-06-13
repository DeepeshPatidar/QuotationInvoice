import sqlite3
from collections.abc import Iterable


class InvoiceRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, invoice_id: int) -> dict | None:
        row = self.conn.execute(
            """
            SELECT id, quotation_id, customer_id, invoice_no, invoice_date,
                   currency, subtotal, tax_percent, tax_amount, total, pdf_path,
                   notes, version, original_invoice_id, status
            FROM invoices WHERE id=?
            """,
            (invoice_id,),
        ).fetchone()
        if not row:
            return None
        keys = (
            "id", "quotation_id", "customer_id", "invoice_no", "invoice_date",
            "currency", "subtotal", "tax_percent", "tax_amount", "total",
            "pdf_path", "notes", "version", "original_invoice_id", "status",
        )
        return dict(zip(keys, row))

    def list_rows(self, keyword: str = "", status: str = "") -> list[tuple]:
        joins = ""
        where = ""
        params: tuple[str, ...] = ()
        if keyword.strip():
            joins = "LEFT JOIN customers c ON i.customer_id = c.id"
            like = f"%{keyword.strip()}%"
            where = """
                WHERE i.invoice_no LIKE ? OR c.name LIKE ? OR i.invoice_date LIKE ?
            """
            params = (like, like, like)
        elif status and status != "All":
            where = "WHERE i.status = ?"
            params = (status,)
        return self.conn.execute(
            f"""
            SELECT i.id, i.invoice_no, i.invoice_date, i.total, i.status
            FROM invoices i
            {joins}
            {where}
            ORDER BY i.invoice_date DESC, i.invoice_no DESC
            """,
            params,
        ).fetchall()

    def replace_items(self, invoice_id: int, items: Iterable[dict]) -> None:
        with self.conn:
            self.conn.execute(
                "DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,)
            )
            self.conn.executemany(
                """
                INSERT INTO invoice_items
                    (invoice_id, item_description, item_code, qty, unit,
                     unit_price, line_total, sac_hsn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        invoice_id,
                        item["description"],
                        item.get("item_code", item.get("code", "")),
                        item["qty"],
                        item.get("unit", ""),
                        item["unit_price"],
                        item["line_total"],
                        item.get("sac_hsn", ""),
                    )
                    for item in items
                ),
            )
