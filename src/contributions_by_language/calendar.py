from datetime import date


def shift_month(month: date, offset: int) -> date:
    """Shift a date by calendar months and return the first day of the result."""
    year, index = divmod(month.year * 12 + month.month - 1 + offset, 12)
    return date(year, index + 1, 1)
