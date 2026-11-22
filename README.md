# Contributions by language

A command-line tool that generates bar, line and stacked area charts in SVG format for a GitHub profile README. The charts show commit contributions by the primary language of each repository for calendar years, quarters or months.

![Yearly GitHub commits by repository language](contributions.svg)

## Generate the chart

Run with Python 3.14 and uv. Set `GITHUB_TOKEN` (or `GH_TOKEN`) in your shell:

```sh
export GITHUB_TOKEN='your-github-token'
uv run contributions-by-language username --years 5
```

If you already use an authenticated GitHub CLI, you can pass its token for this command only:

```sh
GITHUB_TOKEN="$(gh auth token)" uv run contributions-by-language username --years 5
```

You can also put the token in a file named `.env` in the project directory:

```dotenv
GITHUB_TOKEN=your-github-token
```

Pass `--env-file .env` to have uv load the token for the command:

```sh
uv run --env-file .env contributions-by-language username --years 5
```

If your token is issued for more than three months, some organizations may
block it under their [maximum token lifetime policy](https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/setting-a-personal-access-token-policy-for-your-organization#enforcing-a-maximum-lifetime-policy-for-personal-access-tokens).
Commits in those organizations can then be missing from the chart. Use a token
with a lifetime of 90 days or less to reduce this risk. If you replace a token
that had limited access, run once with `--refresh-cache` to reload historical data.

Copy the generated `contributions.svg` to the root of your profile repository (for example, `username/username`) and add this to its README.

```markdown
![Yearly GitHub commits by repository language](./contributions.svg)
```

Run the command again to refresh the chart. Use `--output path.svg` to write directly to an existing local checkout of the profile repository.
The command reports how many months it has fetched from GitHub on standard error.

The default theme is light. To generate a dark chart as a separate SVG, run:

```sh
uv run --env-file .env contributions-by-language username --theme dark --output contributions-dark.svg
```

## Include all available history

```sh
uv run --env-file .env contributions-by-language username --all-time
```

With `GITHUB_TOKEN` or `GH_TOKEN` already set in your environment, omit `--env-file .env`.
The chart starts with the earliest month that has a visible public commit contribution and
includes years without activity through the current year. Use `--years N`
to show the current UTC year and the preceding `N - 1` calendar years. The default
is five years unless a period is set in the settings file.

Use `--group-by quarter` or `--group-by month` to show more detail within
each year. Bars in these modes touch, and the horizontal axis shows one label
per year. The first and last years occupy a full calendar year, with empty
space for periods outside the available data. Segment tooltips identify the quarter or month. The default is
`--group-by year`.

Use `--chart-type line` for a smoothed line per language or `--chart-type bar`
for stacked bars. Lines reach zero on either side of a gap and break between
consecutive periods with zero commits.
Use `--chart-type area` for a smoothed stacked area chart. Each band shows the
commits for one language, and the top edge shows the total for each period.
Languages are stacked from bottom to top in order of first appearance.

## Settings file

The command loads `contributions.toml` from the current directory if it exists.

```toml
login = "username"
all_time = true
theme = "dark"
group_by = "year"
chart_type = "bar"
max_colors = 6
force_other_languages = ["SCSS", "Jupyter Notebook", "JavaScript"]
output = "contributions-dark.svg"
```

With the GitHub token in `.env`, run the command without repeating those settings:

```sh
uv run --env-file .env contributions-by-language
```

Use `--config path/to/settings.yaml` to select another file. TOML, YAML and JSON
are supported. Command-line arguments take priority over file settings. For
example, `--years 3` overrides `all_time = true`. The settings file can use
either `all_time = true` or `years = 3`, and can also set `refresh_cache` to a
boolean. Keep the token in `GITHUB_TOKEN` or `GH_TOKEN`.

Languages listed in `force_other_languages` always go under **Other languages**.
Language names are matched case-insensitively.
Set `show_other_languages = false` or pass `--no-show-other-languages` to hide
this group. Its commits are excluded from chart totals. Pass
`--show-other-languages` to show the group again for a run.

Commit counts appear in the legend by default. Set `show_legend_counts = false`
in the settings file or pass `--no-show-legend-counts` to hide them. Pass
`--show-legend-counts` to enable them again for a run.

## Daily updates with GitHub Actions

Add a repository Actions secret named `CONTRIBUTIONS_TOKEN` containing the
GitHub token used to read contribution data. The **Update contributions chart**
workflow runs daily at 01:00 UTC and can also be started from the Actions tab.
It reads `contributions.toml` and pushes changes to the generated SVG and
historical cache to the default branch using the workflow's GitHub token.
The separate **Check contributions chart** workflow verifies SVG generation
from the committed cache on pushes and pull requests. It uses read-only
permissions and requires no contribution token.

## Local cache

The first run downloads the requested history, with up to four GitHub requests
in flight at a time. Subsequent runs reuse completed UTC
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
- Months are in UTC and include the current partial month. Set `max_colors` in the file or pass `--max-colors` to limit the palette to 2–12 colors (default: 6). The limit includes **No primary language** in gray and **Other languages** in blue-gray when those categories appear.
- Both themes use language colors from a bundled [GitHub Linguist snapshot](https://github.com/github-linguist/linguist/blob/cfd7a0113aa1efab99faeff38756f0ed4d48add8/lib/linguist/languages.yml), with theme palette colors as a fallback.
