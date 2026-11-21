import os
import sys
from datetime import UTC, datetime

from pydantic import ValidationError
from yaml import YAMLError

from .cache import MonthCache
from .calendar import shift_month
from .chart import render_svg
from .history import fetch_history, fetch_months
from .settings import load_settings


def main() -> None:
    try:
        settings = load_settings(sys.argv[1:])
    except (OSError, TypeError, ValueError, YAMLError) as error:
        raise SystemExit(f"Invalid settings: {error}") from None

    login = settings.login
    if not login:
        raise SystemExit("Provide a GitHub username as LOGIN or set login in the settings file.")
    if not (token := os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        raise SystemExit("Set GITHUB_TOKEN or GH_TOKEN.")

    now = datetime.now(UTC).replace(microsecond=0)
    try:
        cache = MonthCache(login)
        if settings.all_time:
            monthly = fetch_history(login, token, now, cache, refresh=settings.refresh_cache)
        else:
            current_month = now.date().replace(day=1)
            months = settings.months if settings.months is not None else 12
            period = [shift_month(current_month, offset) for offset in range(1 - months, 1)]
            monthly = fetch_months(login, token, period, now, cache, refresh=settings.refresh_cache)
        svg = render_svg(
            monthly, login, theme=settings.theme, max_colors=settings.max_colors,
            force_other_languages=settings.force_other_languages,
        )
        settings.output.write_text(svg, encoding="utf-8")
    except ValidationError as error:
        raise SystemExit(
            f"Invalid response from GitHub API ({error.error_count()} validation errors)"
        ) from None
    except (RuntimeError, OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
