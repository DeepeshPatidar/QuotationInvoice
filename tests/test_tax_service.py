import unittest
from decimal import Decimal

from app.services.tax_service import TaxService


class TaxServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = TaxService()

    def test_calculates_discount_and_tax_with_decimal_rounding(self):
        result = self.service.calculate(
            [{"description": "Driver service", "qty": 2, "unit_price": "100"}],
            tax_percent=18,
            discount_percent=10,
        )

        self.assertEqual(result.subtotal, Decimal("200.00"))
        self.assertEqual(result.discount_amount, Decimal("20.00"))
        self.assertEqual(result.tax_amount, Decimal("32.40"))
        self.assertEqual(result.total, Decimal("212.40"))

    def test_rejects_invalid_discount(self):
        with self.assertRaises(ValueError):
            self.service.calculate([], discount_percent=101)


if __name__ == "__main__":
    unittest.main()
