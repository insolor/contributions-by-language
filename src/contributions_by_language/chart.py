from collections import Counter
from collections.abc import Sequence
from datetime import date
from xml.etree.ElementTree import Element, SubElement, tostring

from .palette import DEFAULT_MAX_COLORS, PALETTES

NO_PRIMARY_LANGUAGE = "No primary language"


def render_svg(
    monthly: dict[date, Counter[str]],
    login: str,
    *,
    theme: str = "light",
    max_colors: int = DEFAULT_MAX_COLORS,
    force_other_languages: Sequence[str] = (),
    show_legend_counts: bool = True,
) -> str:
    palette = PALETTES[theme]
    colors = palette.languages

    annual: dict[int, Counter[str]] = {}
    for month, counts in sorted(monthly.items()):
        year_counts = annual.setdefault(month.year, Counter())
        year_counts.update(counts)

    totals = sum(annual.values(), Counter())
    has_no_primary = NO_PRIMARY_LANGUAGE in totals
    forced_names = {name.casefold() for name in force_other_languages}
    forced = {
        name
        for name in totals
        if name != NO_PRIMARY_LANGUAGE and name.casefold() in forced_names
    }
    has_other = bool(forced) or len(totals) > max_colors
    language_slots = max_colors - has_no_primary - has_other
    languages = sorted(
        (name for name in totals if name != NO_PRIMARY_LANGUAGE and name not in forced),
        key=lambda name: (-totals[name], name),
    )[:language_slots]
    series = list(zip(languages, colors, strict=False))
    if has_no_primary:
        series.append((NO_PRIMARY_LANGUAGE, palette.no_language))
    if has_other:
        series.append(("Other languages", colors[-1]))

    width = max(500, 80 + len(annual) * 39)
    legend_columns = max(1, min(3, len(series)))
    legend_rows = (len(series) + legend_columns - 1) // legend_columns
    height = 290 + 24 * legend_rows
    svg = Element(
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
    title = f"Yearly GitHub commits by language · @{login}"
    SubElement(svg, "title", id="title").text = title
    SubElement(svg, "desc", id="description").text = ". ".join(
        f"{year}: "
        + (
            ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
            or "0 commits"
        )
        for year, counts in annual.items()
    )

    def rectangle(x, y, w, h, color, **attributes):
        return SubElement(
            svg,
            "rect",
            x=str(x),
            y=str(y),
            width=str(w),
            height=str(h),
            fill=color,
            **attributes,
        )

    def label(x, y, value, **attributes):
        SubElement(
            svg,
            "text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": "11",
                "fill": palette.foreground,
                **attributes,
            },
        ).text = str(value)

    rectangle(
        0.5,
        0.5,
        width - 1,
        height - 1,
        palette.background,
        **{
            "rx": "11.5",
            "stroke": "#ffffff",
            "stroke-width": "1",
        },
    )
    label(24, 33, title, **{"font-size": "18", "font-weight": "600"})
    peak = max((sum(counts.values()) for counts in annual.values()), default=0)
    axis_max = max(4, ((peak + 3) // 4) * 4)
    baseline = 224
    plot_height = 156
    left = 56
    plot_width = width - left - 24
    step = plot_width / max(1, len(annual))
    bar_width = min(32, step * 0.7)

    for tick in range(5):
        y = baseline - tick * plot_height / 4
        rectangle(left, y, plot_width, 1, palette.grid)
        label(left - 7, y + 4, tick * axis_max // 4, **{"text-anchor": "end"})

    legend = {}
    legend_counts: Counter[str] = Counter()
    for index, (year, counts) in enumerate(annual.items()):
        x = left + (index + 0.5) * step
        values = [counts[name] for name, _ in series]
        total = sum(counts.values())
        if has_other:
            values[-1] = total - sum(values[:-1])

        y = baseline
        for (name, color), count in zip(series, values, strict=True):
            if count:
                legend.setdefault(name, color)
                legend_counts[name] += count
                segment_height = count * plot_height / axis_max
                y -= segment_height
                bar = rectangle(x - bar_width / 2, y, bar_width, segment_height, color)
                SubElement(bar, "title").text = f"{year}, {name}: {count}"
        if total:
            label(x, y - 5, total, **{"text-anchor": "middle"})
        label(x, baseline + 20, year, **{"text-anchor": "middle"})

    if not peak:
        label(
            width / 2,
            145,
            "No public commit contributions in this period",
            **{"text-anchor": "middle"},
        )

    legend_top = 275
    column_width = (width - 50) / legend_columns
    for index, (name, color) in enumerate(legend.items()):
        row, column = divmod(index, legend_columns)
        x = 25 + column * column_width
        y = legend_top + 24 * row
        rectangle(x, y - 9, 10, 10, color)
        legend_label = f"{name} ({legend_counts[name]})" if show_legend_counts else name
        label(x + 17, y, legend_label)

    return tostring(svg, encoding="unicode") + "\n"
