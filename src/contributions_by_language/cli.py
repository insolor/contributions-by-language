import os
from datetime import UTC, datetime
from pathlib import Path

import click
from pydantic import ValidationError

from .cache import MonthCache
from .calendar import shift_month
from .chart import render_svg
from .history import fetch_history, fetch_months


@click.command()
@click.argument("login")
@click.option("--all-time", is_flag=True, help="Include all available commit history.")
@click.option(
    "--months", type=click.IntRange(1, 60), default=12, show_default=True,
    help="Calendar months including the current UTC month.",
)
@click.option(
    "--output", type=click.Path(dir_okay=False, path_type=Path),
    default="contributions.svg", show_default=True,
)
@click.option("--refresh-cache", is_flag=True, help="Fetch closed months again and update the cache.")
@click.pass_context
def main(
    ctx: click.Context, login: str, all_time: bool, months: int, output: Path,
    refresh_cache: bool,
) -> None:
    """Generate an SVG of yearly GitHub commits for LOGIN."""
    if all_time and ctx.get_parameter_source("months") == click.core.ParameterSource.COMMANDLINE:
        raise click.UsageError("--all-time and --months are mutually exclusive")
    if not (token := os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        raise click.UsageError("set GITHUB_TOKEN or GH_TOKEN")

    now = datetime.now(UTC).replace(microsecond=0)
    try:
        cache = MonthCache(login)
        if all_time:
            monthly = fetch_history(login, token, now, cache, refresh=refresh_cache)
        else:
            current_month = now.date().replace(day=1)
            period = [shift_month(current_month, offset) for offset in range(1 - months, 1)]
            monthly = fetch_months(login, token, period, now, cache, refresh=refresh_cache)
        output.write_text(render_svg(monthly, login), encoding="utf-8")
    except ValidationError as error:
        raise click.ClickException(
            f"Invalid response from GitHub API ({error.error_count()} validation errors)"
        ) from error
    except (RuntimeError, OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
