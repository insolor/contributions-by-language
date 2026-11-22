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
    include_private: bool = False,
) -> dict[date, Counter[str]]:
    """Load monthly counts from the cache or concurrent GitHub requests."""
    current_month = now.date().replace(day=1)
    monthly = {}
    pending = []
    for month in months:
        cached = (
            cache.get(month, include_private=include_private)
            if month < current_month and not refresh
            else None
        )
        if cached is None:
            pending.append(month)
        else:
            monthly[month] = cached

    if not pending:
        return monthly

    limit = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def download(month: date) -> tuple[date, Counter[str], Counter[str] | None]:
        """Fetch one month within the concurrent request limit."""
        async with limit:
            counts, private_counts = await fetch_month(
                client, login, month, now, include_private=include_private
            )
            return month, counts, private_counts

    with tqdm(
        total=len(pending), desc="Fetching commit counts", unit="month", file=sys.stderr
    ) as progress:
        requests = [asyncio.create_task(download(month)) for month in pending]
        try:
            async for request in asyncio.as_completed(requests):
                month, counts, private_counts = request.result()
                if month < current_month:
                    cache.put(month, counts, private_counts=private_counts)
                if private_counts is not None:
                    counts.update(private_counts)
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
    include_private: bool = False,
) -> dict[date, Counter[str]]:
    """Load the contribution history through the current month."""
    print("Looking up contribution years…", file=sys.stderr, flush=True)
    years = sorted(await fetch_years(client, login))
    year_list = ", ".join(map(str, years)) or "none"
    print(f"Contribution years: {year_list}", file=sys.stderr, flush=True)
    current_month = now.date().replace(day=1)
    months = [
        date(year, month, 1)
        for year in years
        for month in range(1, 13)
        if (year, month) <= (now.year, now.month)
    ]
    if not months or months[-1] != current_month:
        months.append(current_month)
    fetched = await fetch_months(
        client,
        login,
        months,
        now,
        cache,
        refresh=refresh,
        include_private=include_private,
    )
    month = next((month for month, counts in fetched.items() if counts), current_month)
    monthly = {}
    while month <= current_month:
        monthly[month] = fetched.get(month, Counter())
        month = shift_month(month, 1)
    return monthly
