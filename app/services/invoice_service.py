from quotation_tool import InvoiceService as LegacyInvoiceService

from .tax_service import TaxService


class InvoiceService(LegacyInvoiceService):
    """Invoice workflow using the shared Decimal-based tax calculator."""

    def __init__(
        self,
        db,
        pdf_maker,
        currency="INR",
        tax_percent=18.0,
        tax_service=None,
    ):
        super().__init__(db, pdf_maker, currency, tax_percent)
        self.tax_service = tax_service or TaxService()

    def calculate_totals(self, line_items):
        calculation = self.tax_service.calculate(
            line_items, tax_percent=self.tax_percent
        )
        return (
            list(calculation.items),
            float(calculation.subtotal),
            float(calculation.tax_amount),
            float(calculation.total),
        )
