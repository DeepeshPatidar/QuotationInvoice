from quotation_tool import QuotationService as LegacyQuotationService

from .tax_service import TaxService


class QuotationService(LegacyQuotationService):
    """Quotation workflow exposed through the application service layer."""

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

    def calculate_totals(self, line_items, discount_percent=0):
        return self.tax_service.calculate(
            line_items,
            tax_percent=self.tax_percent,
            discount_percent=discount_percent,
        )
