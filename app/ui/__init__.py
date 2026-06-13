"""PyQt presentation layer."""

from .customers_tab import CustomersTab
from .invoices_tab import InvoicesTab
from .items_tab import ItemsTab
from .main_window import MainWindow
from .proforma_tab import ItemEditDialog, ProformaEditDialog, ProformaInvoiceTab
from .quotations_tab import QuotationsTab
from .settings_tab import SettingsTab

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
]
