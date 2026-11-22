from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, NonNegativeInt


class Language(BaseModel):
    """Represent a programming language returned by GitHub."""

    name: str


class Repository(BaseModel):
    """Represent the visibility and primary language of a repository."""

    visibility: str
    primary_language: Language | None = Field(alias="primaryLanguage")


class CommitDay(BaseModel):
    """Represent the commits GitHub attributes to one day."""

    occurred_at: AwareDatetime = Field(alias="occurredAt")
    commit_count: NonNegativeInt = Field(alias="commitCount")


class PageInfo(BaseModel):
    """Represent whether a GraphQL connection has more results."""

    has_next_page: bool = Field(alias="hasNextPage")


class CommitDays(BaseModel):
    """Represent a page of daily commit contributions."""

    page_info: PageInfo = Field(alias="pageInfo")
    nodes: list[CommitDay]


class RepositoryCommits(BaseModel):
    """Associate a repository with its daily commit contributions."""

    repository: Repository
    contributions: CommitDays


class MonthlyContributions(BaseModel):
    """Represent a month of commit contributions grouped by repository."""

    repository_count: NonNegativeInt = Field(
        alias="totalRepositoriesWithContributedCommits"
    )
    repositories: list[RepositoryCommits] = Field(
        alias="commitContributionsByRepository"
    )


class ContributionYears(BaseModel):
    """Represent the years in a user's contribution history."""

    years: list[Annotated[int, Field(ge=1, le=9999)]] = Field(alias="contributionYears")


class GraphQLError(BaseModel):
    """Represent an error reported by the GraphQL API."""

    message: str


class GraphQLUser[Collection](BaseModel):
    """Wrap a user's contribution collection in a GraphQL result."""

    collection: Collection = Field(alias="contributionsCollection")


class GraphQLData[Collection](BaseModel):
    """Represent the user field in the GraphQL response data."""

    user: GraphQLUser[Collection] | None


class GraphQLResponse[Collection](BaseModel):
    """Wrap typed GraphQL data and any accompanying errors."""

    data: GraphQLData[Collection] | None = None
    errors: list[GraphQLError] = Field(default_factory=list)
