"""Money formatting at the edges. Amounts are always integer paise (ADR-009)."""


def group_indian(n: int) -> str:
    """12345678 -> '1,23,45,678' (Indian digit grouping: last 3, then pairs)."""
    digits = str(abs(n))
    head, tail = digits[:-3], digits[-3:]
    groups: list[str] = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    grouped = ",".join([*groups, tail])
    return f"-{grouped}" if n < 0 else grouped


def format_inr(paise: int) -> str:
    """460000000 -> '₹46,00,000'. Whole rupees (rounded half up)."""
    rupees = (abs(paise) + 50) // 100
    sign = "-" if paise < 0 else ""
    return f"{sign}₹{group_indian(rupees)}"
