from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, NonNegativeInt


class Language(BaseModel):
    name: str


class Repository(BaseModel):
    visibility: str
    primary_language: Language | None = Field(alias="primaryLanguage")


class CommitDay(BaseModel):
    occurred_at: AwareDatetime = Field(alias="occurredAt")
    commit_count: NonNegativeInt = Field(alias="commitCount")


class PageInfo(BaseModel):
    has_next_page: bool = Field(alias="hasNextPage")


class CommitDays(BaseModel):
    page_info: PageInfo = Field(alias="pageInfo")
    nodes: list[CommitDay]


class RepositoryCommits(BaseModel):
    repository: Repository
    contributions: CommitDays


class MonthlyContributions(BaseModel):
    repository_count: NonNegativeInt = Field(
        alias="totalRepositoriesWithContributedCommits"
    )
    repositories: list[RepositoryCommits] = Field(
        alias="commitContributionsByRepository"
    )


class ContributionYears(BaseModel):
    years: list[Annotated[int, Field(ge=1, le=9999)]] = Field(alias="contributionYears")


class GraphQLError(BaseModel):
    message: str


class GraphQLUser[Collection](BaseModel):
    collection: Collection = Field(alias="contributionsCollection")


class GraphQLData[Collection](BaseModel):
    user: GraphQLUser[Collection] | None


class GraphQLResponse[Collection](BaseModel):
    data: GraphQLData[Collection] | None = None
    errors: list[GraphQLError] = Field(default_factory=list)
