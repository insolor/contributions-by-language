# Contributions by language

A command-line tool that generates a stacked bar chart in SVG format for a GitHub profile README. Each bar shows the selected period's commit contributions for a calendar year, grouped by the primary language of each repository.

## Generate the chart

Run with Python 3.14 and uv. Supply a GitHub token in `GITHUB_TOKEN` or `GH_TOKEN`. If you already use an authenticated GitHub CLI, you can pass its token for this command only.

```sh
GITHUB_TOKEN="$(gh auth token)" uv run contributions-by-language insolor --months 12
```

Copy the generated `contributions.svg` to the root of your profile repository (for example, `insolor/insolor`) and add this to its README.

```markdown
![Yearly GitHub commits by repository language](./contributions.svg)
```

Run the command again to refresh the chart. Use `--output path.svg` to write directly to an existing local checkout of the profile repository.
The command reports how many months it has fetched from GitHub on standard error.

## Include all available history

```sh
uv run --env-file .env contributions-by-language insolor --all-time
```

With `GITHUB_TOKEN` or `GH_TOKEN` already set in your environment, omit `--env-file .env`.
The chart starts with the earliest month that has a visible public commit contribution and
includes years without activity through the current year. With `--months`, each
bar includes only the months in the selected period.

## Local cache

The first run downloads the requested history. Subsequent runs reuse completed UTC
months from the local cache and fetch the current month again. In `--all-time`
mode, the list of contribution years is refreshed on each run.

Each year is a JSONL file under `cache/github-<login>/YYYY.jsonl` in the current
Git repository. Each line records a completed month and its language counts.
Outside a Git
repository, the cache goes in the current directory. You can commit these files
and reuse them in another checkout. They contain only language names and commit
counts from public repositories. Use `--refresh-cache` to fetch the requested
months again, for example after a repository's primary language changes.

## What the chart counts

- GitHub [commit contributions](https://docs.github.com/en/graphql/reference/users#createdcommitcontribution) for public repositories. Issues, pull requests, reviews and contributions the API token cannot see are excluded.
- Each commit is assigned to the repository's [primary language reported at fetch time](https://docs.github.com/en/graphql/reference/objects#repository). For multilingual repositories, all of their commits go into that one language.
- Months are in UTC and include the current partial month. The chart uses up to nine colors in total. **No primary language** is gray. When the categories exceed the limit, the most active languages have their own colors and the rest are grouped under **Other languages** in yellow-green.
