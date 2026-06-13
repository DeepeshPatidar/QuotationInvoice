from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class DocumentItem:
    description: str
    qty: Decimal
    unit_price: Decimal
    unit: str = ""
    item_code: str = ""
    sac_hsn: str = ""

    def validate(self) -> None:
        if not self.description.strip():
            raise ValueError("Item description is required")
        if self.qty <= 0:
            raise ValueError("Item quantity must be greater than zero")
        if self.unit_price < 0:
            raise ValueError("Item unit price cannot be negative")


@dataclass(slots=True)
class Quotation:
    customer_id: int
    items: list[DocumentItem] = field(default_factory=list)
    notes: str = ""
    discount_percent: Decimal = Decimal("0")
    id: int | None = None
    quote_no: str = ""
