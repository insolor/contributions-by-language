from collections import Counter
from collections.abc import Sequence
from datetime import date

from .palette import Palette, linguist_colors
from .svg_chart import ChartData, ChartType, GroupBy, period_label

NO_PRIMARY_LANGUAGE = "No primary language"
OTHER_LANGUAGES = "Other languages"


def _series_counts(
    counts: Counter[str], series: Sequence[tuple[str, str]], has_other: bool
) -> list[int]:
    """Align a period's counts with the selected chart series."""
    values = [counts[name] for name, _ in series]
    if has_other:
        values[-1] = sum(counts.values()) - sum(values[:-1])
    return values


def _get_stack_order(
    monthly_items: Sequence[tuple[date, Counter[str]]],
    series: Sequence[tuple[str, str]],
    has_other: bool,
) -> list[int]:
    """Order area layers by the first month with commits in each series."""
    return list(
        dict.fromkeys(
            index
            for _, counts in monthly_items
            for index, count in enumerate(_series_counts(counts, series, has_other))
            if count
        )
    )


def _aggregate_periods(
    monthly_items: Sequence[tuple[date, Counter[str]]], months_per_bar: int
) -> dict[date, Counter[str]]:
    """Sum monthly counts into the requested calendar periods."""
    periods: dict[date, Counter[str]] = {}
    for month, counts in monthly_items:
        start_month = (month.month - 1) // months_per_bar * months_per_bar + 1
        period = date(month.year, start_month, 1)
        periods.setdefault(period, Counter()).update(counts)

    return periods


def _select_series(
    totals: Counter[str],
    palette: Palette,
    *,
    max_colors: int,
    force_other_languages: Sequence[str],
    show_other_languages: bool,
) -> tuple[list[tuple[str, str]], bool]:
    """Select the displayed categories and assign their colors."""
    has_no_primary = NO_PRIMARY_LANGUAGE in totals
    forced_names = {name.casefold() for name in force_other_languages}
    forced = {
        name
        for name in totals
        if name != NO_PRIMARY_LANGUAGE and name.casefold() in forced_names
    }
    has_other = show_other_languages and (bool(forced) or len(totals) > max_colors)
    language_slots = max_colors - has_no_primary - has_other
    languages = sorted(
        (name for name in totals if name != NO_PRIMARY_LANGUAGE and name not in forced),
        key=lambda name: (-totals[name], name),
    )[:language_slots]
    named_colors = linguist_colors() if palette.use_linguist else {}
    series = [
        (name, named_colors.get(name.casefold(), fallback))
        for name, fallback in zip(languages, palette.languages, strict=False)
    ]
    if has_no_primary:
        series.append((NO_PRIMARY_LANGUAGE, palette.no_language))
    if has_other:
        series.append((OTHER_LANGUAGES, palette.other_languages))
    return series, has_other


def _complete_plot_periods(
    periods: dict[date, Counter[str]], months_per_bar: int, chart_type: ChartType
) -> dict[date, Counter[str]]:
    """Fill missing slots across the displayed calendar years."""
    plot_periods = periods
    if periods and (months_per_bar < 12 or chart_type != "bar"):
        first_year = next(iter(periods)).year
        last_year = next(reversed(periods)).year
        plot_periods = {}
        for year in range(first_year, last_year + 1):
            for month_number in range(1, 13, months_per_bar):
                period = date(year, month_number, 1)
                plot_periods[period] = periods.get(period, Counter())

    return plot_periods


def _get_legend_entries(
    values: dict[date, list[int]],
    series: Sequence[tuple[str, str]],
    stack_order: Sequence[int],
) -> list[tuple[str, str, int]]:
    """Summarize series counts and place special categories last."""
    legend_entries = [
        (*series[index], sum(row[index] for row in values.values()))
        for index in stack_order
    ]
    special_order = {OTHER_LANGUAGES: 1, NO_PRIMARY_LANGUAGE: 2}
    legend_entries.sort(key=lambda entry: special_order.get(entry[0], 0))
    return legend_entries


def _describe_periods(periods: dict[date, Counter[str]], group_by: GroupBy) -> str:
    """Describe the recorded counts for the SVG's accessible description."""
    return ". ".join(
        f"{period_label(period, group_by)}: "
        + (
            ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
            or "0 commits"
        )
        for period, counts in periods.items()
    )


def prepare_chart_data(
    monthly: dict[date, Counter[str]],
    title: str,
    palette: Palette,
    *,
    max_colors: int,
    force_other_languages: Sequence[str],
    show_other_languages: bool,
    group_by: GroupBy,
    chart_type: ChartType,
) -> ChartData:
    """Prepare series, values, legend entries, and scale for rendering."""
    months_per_bar = {"year": 12, "quarter": 3, "month": 1}[group_by]
    monthly_items = sorted(monthly.items())
    periods = _aggregate_periods(monthly_items, months_per_bar)
    series, has_other = _select_series(
        sum(periods.values(), Counter()),
        palette,
        max_colors=max_colors,
        force_other_languages=force_other_languages,
        show_other_languages=show_other_languages,
    )
    if not show_other_languages:
        displayed = {name for name, _ in series}
        periods = {
            period: Counter(
                {name: count for name, count in counts.items() if name in displayed}
            )
            for period, counts in periods.items()
        }

    plot_periods = _complete_plot_periods(periods, months_per_bar, chart_type)
    first_period = next(iter(periods), None)
    values = {
        period: _series_counts(counts, series, has_other)
        for period, counts in plot_periods.items()
        if chart_type == "bar"
        or period in periods
        or (first_period is not None and period < first_period)
    }
    peak = max((sum(counts.values()) for counts in periods.values()), default=0)
    if chart_type == "line":
        peak = max((count for row in values.values() for count in row), default=0)

    if chart_type == "area":
        stack_order = _get_stack_order(monthly_items, series, has_other)
    else:
        stack_order = list(
            dict.fromkeys(
                index
                for row in values.values()
                for index, count in enumerate(row)
                if count
            )
        )
    legend_entries = _get_legend_entries(values, series, stack_order)
    return ChartData(
        title,
        _describe_periods(periods, group_by),
        list(plot_periods),
        series,
        values,
        stack_order,
        legend_entries,
        peak,
        max(4, ((peak + 3) // 4) * 4),
    )
