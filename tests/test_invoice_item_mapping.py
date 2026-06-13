import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.database import Database
from app.ui.legacy import InvoicesTab


class StubInvoiceService:
    tax_percent = 18

    def _generate_invoice_no(self):
        return "INV-TEST-0001"


class InvoiceItemMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.db.add_item(
            "SUPD service",
            unit="1",
            unit_price=100000,
            sac_hsn="9982",
        )
        self.tab = InvoicesTab(self.db, StubInvoiceService(), None)

    def tearDown(self):
        self.tab.close()
        self.db.conn.close()
        try:
            os.remove(self.path)
        except PermissionError:
            pass

    def test_catalog_item_populates_invoice_columns_in_header_order(self):
        self.tab.add_item_row()
        combo = self.tab.items_table.cellWidget(0, 0)
        combo.setCurrentIndex(1)

        self.assertEqual(self.tab.items_table.item(0, 1).text(), "1")
        self.assertEqual(self.tab.items_table.item(0, 2).text(), "1")
        self.assertEqual(self.tab.items_table.item(0, 3).text(), "100000.00")
        self.assertEqual(self.tab.items_table.item(0, 4).text(), "9982")
        self.assertEqual(self.tab.items_table.item(0, 5).text(), "100000.00")


if __name__ == "__main__":
    unittest.main()
