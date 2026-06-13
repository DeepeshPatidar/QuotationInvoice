from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from .quotation import DocumentItem


class InvoiceStatus(StrEnum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    UNPAID = "Unpaid"
    PARTIALLY_PAID = "Partially Paid"
    PAID = "Paid"
    CANCELLED = "Cancelled"


@dataclass(slots=True)
class Invoice:
    customer_id: int
    items: list[DocumentItem] = field(default_factory=list)
    notes: str = ""
    status: InvoiceStatus = InvoiceStatus.DRAFT
    id: int | None = None
    invoice_no: str = ""
    quotation_id: int | None = None
    subtotal: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
