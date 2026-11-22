from collections import Counter
from collections.abc import Sequence
from datetime import date
from itertools import groupby
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

from .palette import DEFAULT_MAX_COLORS, PALETTES, Palette

type GroupBy = Literal["year", "quarter", "month"]


def _period_label(period: date, group_by: GroupBy) -> str:
    if group_by == "quarter":
        return f"{period.year} Q{(period.month - 1) // 3 + 1}"
    if group_by == "month":
        return f"{period:%Y-%m}"
    return str(period.year)


class _SvgRenderer:
    NO_PRIMARY_LANGUAGE = "No primary language"
    PLOT_LEFT = 56
    PLOT_BASELINE = 224
    PLOT_HEIGHT = 156

    svg: Element

    def __init__(self, palette: Palette) -> None:
        self.palette = palette

    def _rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str,
        **attributes: str,
    ) -> Element:
        return SubElement(
            self.svg,
            "rect",
            x=str(x),
            y=str(y),
            width=str(width),
            height=str(height),
            fill=color,
            **attributes,
        )

    def _label(
        self,
        x: float,
        y: float,
        value: str | int,
        **attributes: str,
    ) -> None:
        SubElement(
            self.svg,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": "11",
                "fill": self.palette.foreground,
                **attributes,
            },
        ).text = str(value)

    @staticmethod
    def _create_svg(width: int, height: int) -> Element:
        return Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "viewBox": f"0 0 {width} {height}",
                "width": str(width),
                "height": str(height),
                "role": "img",
                "aria-labelledby": "title description",
                "font-family": "system-ui, sans-serif",
            },
        )

    def _draw_header(
        self,
        width: int,
        height: int,
        login: str,
        periods: dict[date, Counter[str]],
        group_by: GroupBy,
    ) -> None:
        frequency = {"year": "Yearly", "quarter": "Quarterly", "month": "Monthly"}
        title = f"{frequency[group_by]} GitHub commits by language · @{login}"
        SubElement(self.svg, "title", id="title").text = title
        SubElement(self.svg, "desc", id="description").text = ". ".join(
            f"{_period_label(period, group_by)}: "
            + (
                ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
                or "0 commits"
            )
            for period, counts in periods.items()
        )

        self._rectangle(
            0.5,
            0.5,
            width - 1,
            height - 1,
            self.palette.background,
            **{
                "rx": "11.5",
                "stroke": "#ffffff",
                "stroke-width": "1",
            },
        )
        self._label(
            24,
            33,
            title,
            **{"font-size": "18", "font-weight": "600"},
        )

    def _draw_axis(self, plot_width: int, axis_max: int) -> None:
        for tick in range(5):
            y = self.PLOT_BASELINE - tick * self.PLOT_HEIGHT / 4
            self._rectangle(self.PLOT_LEFT, y, plot_width, 1, self.palette.grid)
            self._label(
                self.PLOT_LEFT - 7,
                y + 4,
                tick * axis_max // 4,
                **{"text-anchor": "end"},
            )

    def _draw_bars(
        self,
        periods: dict[date, Counter[str]],
        group_by: GroupBy,
        series: Sequence[tuple[str, str]],
        has_other: bool,
        plot_width: int,
        axis_max: int,
    ) -> list[tuple[str, str, int]]:
        step = plot_width / max(1, len(periods))
        yearly = group_by == "year"
        bar_width = min(32, step * 0.7) if yearly else step
        legend: dict[str, str] = {}
        legend_counts: Counter[str] = Counter()
        for index, (period, counts) in enumerate(periods.items()):
            x = self.PLOT_LEFT + (index + 0.5) * step
            values = [counts[name] for name, _ in series]
            total = sum(counts.values())
            if has_other:
                values[-1] = total - sum(values[:-1])

            bar_left = x - bar_width / 2 if yearly else self.PLOT_LEFT + index * step
            period_label = _period_label(period, group_by)
            y = self.PLOT_BASELINE
            for (name, color), count in zip(series, values, strict=True):
                if count:
                    legend.setdefault(name, color)
                    legend_counts[name] += count
                    segment_height = count * self.PLOT_HEIGHT / axis_max
                    y -= segment_height
                    bar = self._rectangle(bar_left, y, bar_width, segment_height, color)
                    SubElement(bar, "title").text = f"{period_label}, {name}: {count}"
            if total and yearly:
                self._label(x, y - 5, total, **{"text-anchor": "middle"})

        self._draw_year_markers(periods, step)
        return [(name, color, legend_counts[name]) for name, color in legend.items()]

    def _draw_year_markers(
        self, periods: dict[date, Counter[str]], step: float
    ) -> None:
        start = 0
        for year, group in groupby(periods, key=lambda period: period.year):
            size = sum(1 for _ in group)
            boundary = self.PLOT_LEFT + start * step
            if start:
                self._rectangle(
                    boundary - 0.5,
                    self.PLOT_BASELINE - self.PLOT_HEIGHT,
                    1,
                    self.PLOT_HEIGHT,
                    self.palette.grid,
                )
            self._label(
                self.PLOT_LEFT + (start + size / 2) * step,
                self.PLOT_BASELINE + 20,
                year,
                **{"text-anchor": "middle"},
            )
            start += size

    def _draw_legend(
        self,
        legend: Sequence[tuple[str, str, int]],
        width: int,
        columns: int,
        show_legend_counts: bool,
    ) -> None:
        legend_top = 275
        column_width = (width - 50) / columns
        for index, (name, color, count) in enumerate(legend):
            row, column = divmod(index, columns)
            x = 25 + column * column_width
            y = legend_top + 24 * row
            self._rectangle(x, y - 9, 10, 10, color)
            legend_label = f"{name} ({count})" if show_legend_counts else name
            self._label(x + 17, y, legend_label)

    def render(
        self,
        monthly: dict[date, Counter[str]],
        login: str,
        *,
        max_colors: int = DEFAULT_MAX_COLORS,
        force_other_languages: Sequence[str] = (),
        show_legend_counts: bool = True,
        group_by: GroupBy = "year",
    ) -> str:
        colors = self.palette.languages

        months_per_bar = {"year": 12, "quarter": 3, "month": 1}[group_by]
        periods: dict[date, Counter[str]] = {}
        for month, counts in sorted(monthly.items()):
            start_month = (month.month - 1) // months_per_bar * months_per_bar + 1
            period = date(month.year, start_month, 1)
            periods.setdefault(period, Counter()).update(counts)

        totals = sum(periods.values(), Counter())
        has_no_primary = self.NO_PRIMARY_LANGUAGE in totals
        forced_names = {name.casefold() for name in force_other_languages}
        forced = {
            name
            for name in totals
            if name != self.NO_PRIMARY_LANGUAGE and name.casefold() in forced_names
        }
        has_other = bool(forced) or len(totals) > max_colors
        language_slots = max_colors - has_no_primary - has_other
        languages = sorted(
            (
                name
                for name in totals
                if name != self.NO_PRIMARY_LANGUAGE and name not in forced
            ),
            key=lambda name: (-totals[name], name),
        )[:language_slots]
        series = list(zip(languages, colors, strict=False))
        if has_no_primary:
            series.append((self.NO_PRIMARY_LANGUAGE, self.palette.no_language))
        if has_other:
            series.append(("Other languages", colors[-1]))

        plot_periods = periods
        if periods and months_per_bar < 12:
            first_year = next(iter(periods)).year
            last_year = next(reversed(periods)).year
            plot_periods = {}
            for year in range(first_year, last_year + 1):
                for month in range(1, 13, months_per_bar):
                    period = date(year, month, 1)
                    plot_periods[period] = periods.get(period, Counter())

        year_count = len({period.year for period in plot_periods})
        width = max(500, 80 + year_count * 39)
        legend_columns = max(1, min(3, len(series)))
        legend_rows = (len(series) + legend_columns - 1) // legend_columns
        height = 290 + 24 * legend_rows
        self.svg = self._create_svg(width, height)
        self._draw_header(width, height, login, periods, group_by)
        peak = max((sum(counts.values()) for counts in periods.values()), default=0)
        axis_max = max(4, ((peak + 3) // 4) * 4)
        plot_width = width - self.PLOT_LEFT - 24
        self._draw_axis(plot_width, axis_max)
        legend = self._draw_bars(
            plot_periods,
            group_by,
            series,
            has_other,
            plot_width,
            axis_max,
        )

        if not peak:
            self._label(
                width / 2,
                145,
                "No public commit contributions in this period",
                **{"text-anchor": "middle"},
            )

        self._draw_legend(legend, width, legend_columns, show_legend_counts)
        return tostring(self.svg, encoding="unicode") + "\n"


def render_svg(
    monthly: dict[date, Counter[str]],
    login: str,
    *,
    theme: str = "light",
    max_colors: int = DEFAULT_MAX_COLORS,
    force_other_languages: Sequence[str] = (),
    show_legend_counts: bool = True,
    group_by: GroupBy = "year",
) -> str:
    return _SvgRenderer(PALETTES[theme]).render(
        monthly,
        login,
        max_colors=max_colors,
        force_other_languages=force_other_languages,
        show_legend_counts=show_legend_counts,
        group_by=group_by,
    )
