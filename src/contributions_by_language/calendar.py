from datetime import date


def shift_month(month: date, offset: int) -> date:
    year, index = divmod(month.year * 12 + month.month - 1 + offset, 12)
    return date(year, index + 1, 1)
