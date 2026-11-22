import os
import sys
from datetime import UTC, date, datetime

from pydantic import ValidationError
from yaml import YAMLError

from .cache import MonthCache
from .chart import render_svg
from .history import fetch_history, fetch_months
from .settings import DEFAULT_YEARS, load_settings


def main() -> None:
    try:
        settings = load_settings(sys.argv[1:])
    except (OSError, TypeError, ValueError, YAMLError) as error:
        raise SystemExit(f"Invalid settings: {error}") from None

    login = settings.login
    if not login:
        raise SystemExit(
            "Provide a GitHub username as LOGIN or set login in the settings file."
        )
    if not (token := os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        raise SystemExit("Set GITHUB_TOKEN or GH_TOKEN.")

    now = datetime.now(UTC).replace(microsecond=0)
    try:
        cache = MonthCache(login)
        if settings.all_time:
            monthly = fetch_history(
                login, token, now, cache, refresh=settings.refresh_cache
            )
        else:
            first_year = max(1, now.year - (settings.years or DEFAULT_YEARS) + 1)
            period = [
                date(year, month, 1)
                for year in range(first_year, now.year + 1)
                for month in range(1, (now.month if year == now.year else 12) + 1)
            ]
            monthly = fetch_months(
                login, token, period, now, cache, refresh=settings.refresh_cache
            )
        svg = render_svg(
            monthly,
            login,
            theme=settings.theme,
            max_colors=settings.max_colors,
            force_other_languages=settings.force_other_languages,
            show_legend_counts=settings.show_legend_counts,
            show_other_languages=settings.show_other_languages,
            group_by=settings.group_by,
            chart_type=settings.chart_type,
        )
        settings.output.write_text(svg, encoding="utf-8")
    except ValidationError as error:
        raise SystemExit(
            f"Invalid response from GitHub API ({error.error_count()} validation errors)"
        ) from None
    except (RuntimeError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
