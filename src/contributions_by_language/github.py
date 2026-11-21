import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def fetch_collection[Collection: BaseModel](
    query: str, model: type[Collection], login: str, token: str, **variables: str | int
) -> Collection:
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({
            "query": query,
            "variables": {"login": login, **variables},
        }).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "contributions-by-language",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except HTTPError as error:
        raise RuntimeError(f"GitHub API returned HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"GitHub API request failed: {error.reason}") from error

    envelope = GraphQLResponse[model].model_validate_json(payload)
    if envelope.errors:
        messages = "; ".join(error.message for error in envelope.errors)
        raise RuntimeError(f"GitHub API: {messages}")
    if envelope.data is None:
        raise RuntimeError("GitHub API returned no data")
    if envelope.data.user is None:
        raise RuntimeError(f"GitHub user {login!r} was not found")
    return envelope.data.user.collection


def fetch_month(login: str, token: str, month: date, now: datetime) -> Counter[str]:
    start = datetime.combine(month, time.min, UTC)
    end = datetime.combine(shift_month(month, 1), time.min, UTC)
    collection = fetch_collection(QUERY, MonthlyContributions, login, token, **{
        "from": start.isoformat(),
        "to": min(end - timedelta(seconds=1), now).isoformat(),
        "limit": 100,
    })
    if len(collection.repositories) < collection.repository_count:
        raise RuntimeError(f"GitHub returned an incomplete repository list for {month:%Y-%m}")

    counts = Counter()
    for entry in collection.repositories:
        repository = entry.repository
        if repository.visibility != "PUBLIC":
            continue
        contributions = entry.contributions
        if contributions.page_info.has_next_page:
            raise RuntimeError(f"GitHub returned incomplete daily counts for {month:%Y-%m}")
        language = repository.primary_language
        name = language.name if language else "No primary language"
        for day in contributions.nodes:
            occurred = day.occurred_at
            if start <= occurred < end:
                counts[name] += day.commit_count
    return counts


def fetch_years(login: str, token: str) -> set[int]:
    return set(fetch_collection(YEARS_QUERY, ContributionYears, login, token).years)
