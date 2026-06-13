"""Main application window."""

from PyQt6.QtWidgets import QMainWindow, QTabWidget

from .customers_tab import CustomersTab
from .invoices_tab import InvoicesTab
from .items_tab import ItemsTab
from .proforma_tab import ProformaInvoiceTab
from .quotations_tab import QuotationsTab
from .settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self, db, pdf_maker, quotation_service, invoice_service):
        super().__init__()
        self.setWindowTitle("Quotation Manager")
        self.resize(1000, 700)

        tabs = QTabWidget()
        tabs.addTab(CustomersTab(db), "Customers")
        tabs.addTab(ItemsTab(db), "Items")
        tabs.addTab(QuotationsTab(db, quotation_service), "Quotations")
        tabs.addTab(ProformaInvoiceTab(db, quotation_service), "Proforma Invoices")
        tabs.addTab(InvoicesTab(db, invoice_service, quotation_service), "Invoices")
        tabs.addTab(SettingsTab(pdf_maker, quotation_service), "Settings")
        self.setCentralWidget(tabs)


__all__ = ["MainWindow"]
