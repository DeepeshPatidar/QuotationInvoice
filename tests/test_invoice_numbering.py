import os
import tempfile
import unittest
from unittest.mock import patch

from app.database import Database
from app.services import InvoiceService


class RecordingPdfMaker:
    def __init__(self):
        self.output_paths = []

    def build(self, **kwargs):
        self.output_paths.append(kwargs["output_path"])


class InvoiceNumberingTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.customer_id = self.db.add_customer("Numbering Test Customer")
        self.pdf_maker = RecordingPdfMaker()
        self.service = InvoiceService(self.db, self.pdf_maker)
        self.line_items = [
            {
                "description": "SUPD service",
                "qty": 1,
                "unit": "1",
                "unit_price": 100000,
                "sac_hsn": "9982",
            }
        ]

    def tearDown(self):
        self.db.conn.close()
        try:
            os.remove(self.path)
        except PermissionError:
            pass

    def _create(self, invoice_no, existing_invoice_id=None):
        return self.service.create_invoice(
            customer_id=self.customer_id,
            line_items=self.line_items,
            invoice_no=invoice_no,
            invoice_date="2026-06-13",
            existing_invoice_id=existing_invoice_id,
        )

    def test_financial_year_sequence_uses_simple_incrementing_number(self):
        self.db.set_invoice_sequence("2026-27", 3)

        generated = self.service._generate_invoice_no("2026-06-13")

        self.assertEqual(generated, "INV004")

    def test_stale_duplicate_number_advances_before_pdf_generation(self):
        self.db.set_invoice_sequence("2026-27", 3)
        self._create("INV004")

        result = self._create("INV004")

        self.assertEqual(result["invoice_no"], "INV005")
        self.assertTrue(
            self.pdf_maker.output_paths[-1].endswith("INV005_V1.pdf")
        )

    def test_editing_a_version_creates_clean_next_version(self):
        self.db.set_invoice_sequence("2026-27", 3)
        first = self._create("INV004")
        second = self._create("INV004", first["invoice_id"])

        third = self._create(second["invoice_no"], second["invoice_id"])

        self.assertEqual(second["invoice_no"], "INV004")
        self.assertEqual(second["stored_invoice_no"], "INV004-V2")
        self.assertEqual(third["invoice_no"], "INV004")
        self.assertEqual(third["stored_invoice_no"], "INV004-V3")
        self.assertTrue(
            self.pdf_maker.output_paths[-1].endswith(
                "INV004_V3.pdf"
            )
        )


if __name__ == "__main__":
    unittest.main()
