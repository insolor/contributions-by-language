import asyncio
import sys
from collections import Counter
from datetime import date, datetime

from httpx import AsyncClient
from tqdm import tqdm

from .cache import MonthCache
from .calendar import shift_month
from .github import fetch_month, fetch_years

MAX_CONCURRENT_REQUESTS = 4


async def fetch_months(
    client: AsyncClient,
    login: str,
    months: list[date],
    now: datetime,
    cache: MonthCache,
    *,
    refresh: bool = False,
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

    limit = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def download(month: date) -> tuple[date, Counter[str]]:
        async with limit:
            return month, await fetch_month(client, login, month, now)

    with tqdm(
        total=len(pending), desc="Fetching commit counts", unit="month", file=sys.stderr
    ) as progress:
        requests = [asyncio.create_task(download(month)) for month in pending]
        try:
            async for request in asyncio.as_completed(requests):
                month, counts = request.result()
                if month < current_month:
                    cache.put(month, counts)
                monthly[month] = counts
                progress.update()
        finally:
            for request in requests:
                request.cancel()
            await asyncio.gather(*requests, return_exceptions=True)
    return {month: monthly[month] for month in months}


async def fetch_history(
    client: AsyncClient,
    login: str,
    now: datetime,
    cache: MonthCache,
    *,
    refresh: bool = False,
) -> dict[date, Counter[str]]:
    print("Looking up contribution years…", file=sys.stderr, flush=True)
    years = await fetch_years(client, login)
    current_month = now.date().replace(day=1)
    months = [
        date(year, month, 1)
        for year in sorted(years)
        for month in range(1, 13)
        if (year, month) <= (now.year, now.month)
    ]
    if not months or months[-1] != current_month:
        months.append(current_month)
    fetched = await fetch_months(client, login, months, now, cache, refresh=refresh)
    month = next((month for month, counts in fetched.items() if counts), current_month)
    monthly = {}
    while month <= current_month:
        monthly[month] = fetched.get(month, Counter())
        month = shift_month(month, 1)
    return monthly
