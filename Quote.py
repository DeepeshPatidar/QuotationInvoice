"""Backward-compatible launcher for the layered application."""

from app.main import main
from app.ui.customers_tab import CustomersTab
from app.ui.invoices_tab import InvoicesTab
from app.ui.items_tab import ItemsTab
from app.ui.main_window import MainWindow
from app.ui.proforma_tab import ItemEditDialog, ProformaEditDialog, ProformaInvoiceTab
from app.ui.quotations_tab import QuotationsTab
from app.ui.settings_tab import SettingsTab

__all__ = [
    "CustomersTab",
    "InvoicesTab",
    "ItemEditDialog",
    "ItemsTab",
    "MainWindow",
    "ProformaEditDialog",
    "ProformaInvoiceTab",
    "QuotationsTab",
    "SettingsTab",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
