"""Rupee display formatting shared across services (mirrors utils/format.ts in the app)."""

from decimal import ROUND_FLOOR, Decimal

MINUS = "−"


def whole_rupees(amount: Decimal | int) -> int:
    """Nearest whole rupee with halves going up, like the app's Math.round."""
    return int((Decimal(amount) + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR))


def format_inr(amount: Decimal | int) -> str:
    """Whole rupees with Indian digit grouping: 120000 -> '₹1,20,000', -450 -> '−₹450'."""
    rupees = whole_rupees(amount)
    digits = str(abs(rupees))
    if len(digits) > 3:
        head, groups = digits[:-3], [digits[-3:]]
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups)
    return f"{MINUS if rupees < 0 else ''}₹{digits}"
