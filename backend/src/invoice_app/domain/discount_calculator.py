"""Discount arithmetic for pricing. Independent of approvals; kept from the original demo app."""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Optional


class DiscountCalculator:
    """Volume and loyalty discount rules used when pricing invoices."""

    def quantity_discount(self, quantity: int) -> Decimal:
        """Volume discount rate: 5% from 10 units, 10% from 50, 15% from 100."""
        if quantity >= 100:
            return Decimal("0.15")
        if quantity >= 50:
            return Decimal("0.10")
        if quantity >= 10:
            return Decimal("0.05")
        return Decimal("0")

    def loyalty_discount(self, years_as_customer: int) -> Decimal:
        """Loyalty discount rate: 1% per year as a customer, capped at 10%."""
        return min(Decimal(years_as_customer) * Decimal("0.01"), Decimal("0.10"))

    def combined_discount(self, quantity: int, years_as_customer: int, customer_type: Optional[str]) -> Decimal:
        """Sum of the volume and loyalty rates, plus 5% for a ``Nonprofit`` customer."""
        discount = self.quantity_discount(quantity) + self.loyalty_discount(years_as_customer)
        if customer_type == "Nonprofit":
            discount += Decimal("0.05")
        return discount

    def apply_discount(self, amount: Decimal, discount_rate: Decimal) -> Decimal:
        """Apply a rate to an amount and round to the cent (banker's rounding)."""
        return (amount * (1 - discount_rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
