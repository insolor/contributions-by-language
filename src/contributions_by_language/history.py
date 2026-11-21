import sys
from collections import Counter
from datetime import date, datetime

from tqdm import tqdm

from .cache import MonthCache
from .calendar import shift_month
from .github import fetch_month, fetch_years


def fetch_months(
    login: str, token: str, months: list[date], now: datetime,
    cache: MonthCache, *, refresh: bool = False,
) -> dict[date, Counter[str]]:
    current_month = now.date().replace(day=1)
    monthly = {}
    pending = []
    for month in months:
        cached = cache.get(month) if month < current_month and not refresh else None
        if cached is None:
            pending.append(month)
        else:
            monthly[month] = cached

    if not pending:
        return monthly

    with tqdm(total=len(pending), desc="Fetching commit counts", unit="month", file=sys.stderr) as progress:
        for month in pending:
            counts = fetch_month(login, token, month, now)
            if month < current_month:
                cache.put(month, counts)
            monthly[month] = counts
            progress.set_postfix_str(f"{month:%Y-%m}", refresh=False)
            progress.update()
    return {month: monthly[month] for month in months}


def fetch_history(
    login: str, token: str, now: datetime, cache: MonthCache, *, refresh: bool = False,
) -> dict[date, Counter[str]]:
    print("Looking up contribution years…", file=sys.stderr, flush=True)
    years = fetch_years(login, token)
    current_month = now.date().replace(day=1)
    months = [
        date(year, month, 1)
        for year in sorted(years)
        for month in range(1, 13)
        if (year, month) <= (now.year, now.month)
    ]
    if not months or months[-1] != current_month:
        months.append(current_month)
    fetched = fetch_months(login, token, months, now, cache, refresh=refresh)
    month = next((month for month, counts in fetched.items() if counts), current_month)
    monthly = {}
    while month <= current_month:
        monthly[month] = fetched.get(month, Counter())
        month = shift_month(month, 1)
    return monthly
