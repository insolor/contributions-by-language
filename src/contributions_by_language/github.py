from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

import httpx
from pydantic import BaseModel

from .calendar import shift_month
from .models import ContributionYears, GraphQLResponse, MonthlyContributions

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!, $limit: Int!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalRepositoriesWithContributedCommits
      commitContributionsByRepository(maxRepositories: $limit) {
        repository { visibility primaryLanguage { name } }
        contributions(first: 31) {
          pageInfo { hasNextPage }
          nodes { occurredAt commitCount }
        }
      }
    }
  }
}
"""

YEARS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionYears }
  }
}
"""


async def fetch_collection[Collection: BaseModel](
    client: httpx.AsyncClient,
    query: str,
    model: type[GraphQLResponse[Collection]],
    login: str,
    **variables: str | int,
) -> Collection:
    try:
        response = await client.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"login": login, **variables}},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"GitHub API returned HTTP {error.response.status_code}"
        ) from error
    except httpx.RequestError as error:
        reason = str(error) or type(error).__name__
        raise RuntimeError(f"GitHub API request failed: {reason}") from error

    envelope = model.model_validate_json(response.content)
    if envelope.errors:
        messages = "; ".join(error.message for error in envelope.errors)
        raise RuntimeError(f"GitHub API: {messages}")
    if envelope.data is None:
        raise RuntimeError("GitHub API returned no data")
    if envelope.data.user is None:
        raise RuntimeError(f"GitHub user {login!r} was not found")
    return envelope.data.user.collection


async def fetch_month(
    client: httpx.AsyncClient, login: str, month: date, now: datetime
) -> Counter[str]:
    start = datetime.combine(month, time.min, UTC)
    end = datetime.combine(shift_month(month, 1), time.min, UTC)
    variables: dict[str, str | int] = {
        "from": start.isoformat(),
        "to": min(end - timedelta(seconds=1), now).isoformat(),
        "limit": 100,
    }
    collection = await fetch_collection(
        client, QUERY, GraphQLResponse[MonthlyContributions], login, **variables
    )
    if len(collection.repositories) < collection.repository_count:
        raise RuntimeError(
            f"GitHub returned an incomplete repository list for {month:%Y-%m}"
        )

    counts: Counter[str] = Counter()
    for entry in collection.repositories:
        repository = entry.repository
        if repository.visibility != "PUBLIC":
            continue
        contributions = entry.contributions
        if contributions.page_info.has_next_page:
            raise RuntimeError(
                f"GitHub returned incomplete daily counts for {month:%Y-%m}"
            )
        language = repository.primary_language
        name = language.name if language else "No primary language"
        for day in contributions.nodes:
            occurred = day.occurred_at
            if start <= occurred < end:
                counts[name] += day.commit_count
    return counts


async def fetch_years(client: httpx.AsyncClient, login: str) -> set[int]:
    collection = await fetch_collection(
        client, YEARS_QUERY, GraphQLResponse[ContributionYears], login
    )
    return set(collection.years)
