from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from itertools import groupby, pairwise
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

from .palette import Palette

type GroupBy = Literal["year", "quarter", "month"]
type ChartType = Literal["bar", "line", "area"]


@dataclass(frozen=True)
class ChartData:
    title: str
    description: str
    periods: list[date]
    series: list[tuple[str, str]]
    values: dict[date, list[int]]
    stack_order: list[int]
    legend_entries: list[tuple[str, str, int]]
    peak: int
    axis_max: int


def period_label(period: date, group_by: GroupBy) -> str:
    if group_by == "quarter":
        return f"{period.year} Q{(period.month - 1) // 3 + 1}"
    if group_by == "month":
        return f"{period:%Y-%m}"
    return str(period.year)


def _smooth_curve(points: Sequence[tuple[float, float]]) -> list[str]:
    commands = []
    for (x0, y0), (x1, y1) in pairwise(points):
        midpoint = (x0 + x1) / 2
        commands.append(
            f"C {midpoint:.3f} {y0:.3f} {midpoint:.3f} {y1:.3f} {x1:.3f} {y1:.3f}"
        )
    return commands


class SvgChartRenderer:
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
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "fill": color,
                **attributes,
            },
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
        title: str,
        description: str,
    ) -> None:
        SubElement(self.svg, "title", id="title").text = title
        SubElement(self.svg, "desc", id="description").text = description

        self._rectangle(
            0.5,
            0.5,
            width - 1,
            height - 1,
            self.palette.background,
            **{
                "rx": "4.5",
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
        periods: Sequence[date],
        group_by: GroupBy,
        series: Sequence[tuple[str, str]],
        values_by_period: dict[date, list[int]],
        plot_width: int,
        axis_max: int,
    ) -> None:
        step = plot_width / max(1, len(periods))
        yearly = group_by == "year"
        bar_width = min(32, step * 0.7) if yearly else step
        for index, period in enumerate(periods):
            x = self.PLOT_LEFT + (index + 0.5) * step
            values = values_by_period[period]
            total = sum(values)

            bar_left = x - bar_width / 2 if yearly else self.PLOT_LEFT + index * step
            label = period_label(period, group_by)
            y: float = self.PLOT_BASELINE
            for (name, color), count in zip(series, values, strict=True):
                if count:
                    segment_height = count * self.PLOT_HEIGHT / axis_max
                    y -= segment_height
                    bar = self._rectangle(bar_left, y, bar_width, segment_height, color)
                    SubElement(bar, "title").text = f"{label}, {name}: {count}"
            if total and yearly:
                self._label(x, y - 5, total, **{"text-anchor": "middle"})

        self._draw_year_markers(periods, step)

    def _draw_lines(
        self,
        periods: Sequence[date],
        group_by: GroupBy,
        series: Sequence[tuple[str, str]],
        values_by_period: dict[date, list[int]],
        plot_width: int,
        axis_max: int,
    ) -> None:
        step = plot_width / max(1, len(periods))
        self._draw_year_markers(periods, step)
        for index, (name, color) in enumerate(series):
            counts = [
                values[index]
                if (values := values_by_period.get(period)) is not None
                else None
                for period in periods
            ]
            if not any(counts):
                continue
            visible_counts = [
                count if count or (count == 0 and (previous or following)) else None
                for previous, count, following in zip(
                    [None, *counts[:-1]], counts, [*counts[1:], None], strict=True
                )
            ]
            points = [
                (
                    self.PLOT_LEFT + (position + 0.5) * step,
                    self.PLOT_BASELINE - (count or 0) * self.PLOT_HEIGHT / axis_max,
                    period,
                    count,
                )
                for position, (period, count) in enumerate(
                    zip(periods, visible_counts, strict=True)
                )
            ]
            segments = []
            segment: list[tuple[float, float, date, int | None]] = []
            for point in points:
                count = point[3]
                if segment and (count is None or (count == 0 and segment[-1][3] == 0)):
                    segments.append(segment)
                    segment = []
                if count is not None:
                    segment.append(point)
            if segment:
                segments.append(segment)

            for segment in segments:
                curve = [(x, y) for x, y, _, _ in segment]
                _, _, first_period, first_count = segment[0]
                if group_by == "year" and first_period == periods[0] and first_count:
                    curve.insert(0, (self.PLOT_LEFT, self.PLOT_BASELINE))
                x, y = curve[0]
                if len(curve) == 1:
                    half_width = min(step / 4, 3)
                    commands = [
                        f"M {x - half_width:.3f} {y:.3f} H {x + half_width:.3f}"
                    ]
                else:
                    commands = [f"M {x:.3f} {y:.3f}"]
                    commands.extend(_smooth_curve(curve))
                path = SubElement(
                    self.svg,
                    "path",
                    {
                        "d": " ".join(commands),
                        "fill": "none",
                        "stroke": color,
                        "stroke-width": "2",
                        "stroke-linecap": "round",
                    },
                )
                SubElement(path, "title").text = "\n".join(
                    f"{period_label(period, group_by)}, {name}: {count}"
                    for _, _, period, count in segment
                )

    def _draw_area(
        self,
        periods: Sequence[date],
        group_by: GroupBy,
        series: Sequence[tuple[str, str]],
        stack_order: Sequence[int],
        values_by_period: dict[date, list[int]],
        plot_width: int,
        axis_max: int,
    ) -> None:
        step = plot_width / max(1, len(periods))
        self._draw_year_markers(periods, step)
        if not values_by_period:
            return

        last_period = next(reversed(values_by_period))
        visible_periods = [period for period in periods if period <= last_period]
        empty_row = [0] * len(series)
        rows = [values_by_period.get(period, empty_row) for period in visible_periods]
        xs = [self.PLOT_LEFT + (index + 0.5) * step for index in range(len(rows))]
        scale = self.PLOT_HEIGHT / axis_max
        cumulative = [0] * len(rows)
        for index in stack_order:
            name, color = series[index]
            counts = [row[index] for row in rows]
            lower = [
                (x, self.PLOT_BASELINE - count * scale)
                for x, count in zip(xs, cumulative, strict=True)
            ]
            cumulative = [
                base + count for base, count in zip(cumulative, counts, strict=True)
            ]
            upper = [
                (x, self.PLOT_BASELINE - count * scale)
                for x, count in zip(xs, cumulative, strict=True)
            ]
            if group_by == "year":
                left_edge = (self.PLOT_LEFT, self.PLOT_BASELINE)
                lower.insert(0, left_edge)
                upper.insert(0, left_edge)
            elif len(xs) == 1:
                x, upper_y = upper[0]
                _, lower_y = lower[0]
                upper = [(x - step / 4, upper_y), (x + step / 4, upper_y)]
                lower = [(x - step / 4, lower_y), (x + step / 4, lower_y)]
            lower.reverse()
            x0, y0 = upper[0]
            x1, y1 = lower[0]
            commands = [
                f"M {x0:.3f} {y0:.3f}",
                *_smooth_curve(upper),
                f"L {x1:.3f} {y1:.3f}",
                *_smooth_curve(lower),
                "Z",
            ]
            path = SubElement(self.svg, "path", d=" ".join(commands), fill=color)
            SubElement(path, "title").text = "\n".join(
                f"{period_label(period, group_by)}, {name}: {count}"
                for period, count in zip(visible_periods, counts, strict=True)
                if count
            )

    def _draw_year_markers(self, periods: Sequence[date], step: float) -> None:
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
        data: ChartData,
        *,
        show_legend_counts: bool,
        group_by: GroupBy,
        chart_type: ChartType,
    ) -> str:
        year_count = len({period.year for period in data.periods})
        width = max(500, 80 + year_count * 39)
        legend_columns = max(1, min(3, len(data.series)))
        legend_rows = (len(data.series) + legend_columns - 1) // legend_columns
        height = 290 + 24 * legend_rows
        self.svg = self._create_svg(width, height)
        self._draw_header(width, height, data.title, data.description)
        plot_width = width - self.PLOT_LEFT - 24
        self._draw_axis(plot_width, data.axis_max)
        if chart_type == "line":
            self._draw_lines(
                data.periods,
                group_by,
                data.series,
                data.values,
                plot_width,
                data.axis_max,
            )
        elif chart_type == "area":
            self._draw_area(
                data.periods,
                group_by,
                data.series,
                data.stack_order,
                data.values,
                plot_width,
                data.axis_max,
            )
        else:
            self._draw_bars(
                data.periods,
                group_by,
                data.series,
                data.values,
                plot_width,
                data.axis_max,
            )
        if not data.peak:
            self._label(
                width / 2,
                145,
                "No public commit contributions in this period",
                **{"text-anchor": "middle"},
            )
        self._draw_legend(
            data.legend_entries, width, legend_columns, show_legend_counts
        )
        return tostring(self.svg, encoding="unicode") + "\n"
