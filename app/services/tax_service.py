from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

MONEY_QUANTUM = Decimal("0.01")


def as_money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class TaxCalculation:
    items: tuple[dict, ...]
    subtotal: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    total: Decimal


class TaxService:
    def calculate(
        self,
        line_items,
        tax_percent=Decimal("18"),
        discount_percent=Decimal("0"),
    ) -> TaxCalculation:
        processed_items = []
        subtotal = Decimal("0.00")

        for item in line_items:
            qty = Decimal(str(item.get("qty", 1)))
            unit_price = as_money(item.get("unit_price", 0))
            if qty <= 0:
                raise ValueError("Item quantity must be greater than zero")
            if unit_price < 0:
                raise ValueError("Item unit price cannot be negative")

            line_total = (qty * unit_price).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
            item_code = item.get("item_code", item.get("code", ""))
            processed_items.append(
                {
                    "description": item.get("description", ""),
                    "item_code": item_code,
                    "code": item_code,
                    "qty": float(qty),
                    "unit": item.get("unit", ""),
                    "unit_price": float(unit_price),
                    "line_total": float(line_total),
                    "sac_hsn": item.get("sac_hsn", ""),
                }
            )
            subtotal += line_total

        tax_rate = Decimal(str(tax_percent))
        discount_rate = Decimal(str(discount_percent))
        if not Decimal("0") <= discount_rate <= Decimal("100"):
            raise ValueError("Discount must be between 0 and 100 percent")
        if tax_rate < 0:
            raise ValueError("Tax percentage cannot be negative")

        subtotal = subtotal.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        discount_amount = (
            subtotal * discount_rate / Decimal("100")
        ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        taxable_amount = subtotal - discount_amount
        tax_amount = (
            taxable_amount * tax_rate / Decimal("100")
        ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        total = (taxable_amount + tax_amount).quantize(
            MONEY_QUANTUM, rounding=ROUND_HALF_UP
        )

        return TaxCalculation(
            items=tuple(processed_items),
            subtotal=subtotal,
            discount_percent=discount_rate,
            discount_amount=discount_amount,
            taxable_amount=taxable_amount,
            tax_percent=tax_rate,
            tax_amount=tax_amount,
            total=total,
        )
