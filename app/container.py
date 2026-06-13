from dataclasses import dataclass

from app.database import Database
from app.pdf import DocumentGenerator
from app.services import InvoiceService, QuotationService, TaxService
from quotation_tool import (
    default_invoice_terms,
    default_terms,
    load_company_info,
)


DEFAULT_COMPANY = {
    "name": "Apex Automobile Testing",
    "address": "62 Vrindavan Colony, Gawali Palasiya, MHOW, Indore, MP 453441",
    "phone": "+91-9754220798",
    "email": "deepeshpatidar@hotmail.com",
    "gstin": "23AOHPD5200L1ZD",
}


def _normalise_terms(value, fallback):
    if isinstance(value, str):
        value = value.splitlines()
    return value if isinstance(value, list) and value else fallback()


@dataclass(slots=True)
class ApplicationContainer:
    database: Database
    document_generator: DocumentGenerator
    quotation_service: QuotationService
    invoice_service: InvoiceService

    @classmethod
    def build(cls) -> "ApplicationContainer":
        company = load_company_info(DEFAULT_COMPANY)
        document_generator = DocumentGenerator(
            company_info=company,
            terms=_normalise_terms(company.get("terms"), default_terms),
            invoice_terms=_normalise_terms(
                company.get("invoice_terms"), default_invoice_terms
            ),
            logo_path=company.get("logo_path", ""),
            seal_sign_path=company.get("seal_sign_path", ""),
        )
        database = Database()
        tax_service = TaxService()
        quotation_service = QuotationService(
            database,
            document_generator,
            currency="INR",
            tax_percent=18.0,
            tax_service=tax_service,
        )
        invoice_service = InvoiceService(
            database,
            document_generator,
            currency="INR",
            tax_percent=18.0,
            tax_service=tax_service,
        )
        return cls(
            database=database,
            document_generator=document_generator,
            quotation_service=quotation_service,
            invoice_service=invoice_service,
        )
