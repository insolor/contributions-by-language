from collections import Counter
from datetime import date
from xml.etree.ElementTree import Element, SubElement, tostring

COLORS = (
    "#0047ab", "#e88400", "#007a4d", "#f04c9b",
    "#5d2387", "#00a6c6", "#bb1900", "#63401f",
    "#91a621",
)
NO_PRIMARY_LANGUAGE = "No primary language"


def render_svg(monthly: dict[date, Counter[str]], login: str) -> str:
    annual: dict[int, Counter[str]] = {}
    for month, counts in sorted(monthly.items()):
        year_counts = annual.setdefault(month.year, Counter())
        year_counts.update(counts)

    totals = sum(annual.values(), Counter())
    has_no_primary = NO_PRIMARY_LANGUAGE in totals
    has_other = len(totals) > len(COLORS)
    language_slots = len(COLORS) - has_no_primary - has_other
    languages = sorted(
        (name for name in totals if name != NO_PRIMARY_LANGUAGE),
        key=lambda name: (-totals[name], name),
    )[:language_slots]
    series = [(name, color) for name, color in zip(languages, COLORS)]
    if has_no_primary:
        series.append((NO_PRIMARY_LANGUAGE, "#737373"))
    if has_other:
        series.append(("Other languages", COLORS[-1]))

    width = max(500, 80 + len(annual) * 39)
    legend_columns = max(1, min(3, len(series)))
    legend_rows = (len(series) + legend_columns - 1) // legend_columns
    height = 290 + 24 * legend_rows
    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "viewBox": f"0 0 {width} {height}",
        "width": str(width), "height": str(height), "role": "img",
        "aria-labelledby": "title description", "font-family": "system-ui, sans-serif",
    })
    title = f"Yearly GitHub commits by language · @{login}"
    SubElement(svg, "title", id="title").text = title
    SubElement(svg, "desc", id="description").text = ". ".join(
        f"{year}: " + (", ".join(f"{name} {count}" for name, count in sorted(counts.items())) or "0 commits")
        for year, counts in annual.items()
    )

    def rectangle(x, y, w, h, color, **attributes):
        return SubElement(svg, "rect", x=str(x), y=str(y), width=str(w), height=str(h), fill=color, **attributes)

    def label(x, y, value, **attributes):
        SubElement(svg, "text", {"x": str(x), "y": str(y), "font-size": "11", "fill": "#1e293b", **attributes}).text = str(value)

    rectangle(0, 0, width, height, "#f8fafc", rx="12")
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
        rectangle(left, y, plot_width, 1, "#cbd5e1")
        label(left - 7, y + 4, tick * axis_max // 4, **{"text-anchor": "end"})

    legend = {}
    for index, (year, counts) in enumerate(annual.items()):
        x = left + (index + 0.5) * step
        values = [counts[name] for name, _ in series]
        total = sum(counts.values())
        if has_other:
            values[-1] = total - sum(values[:-1])

        y = baseline
        for (name, color), count in zip(series, values):
            if count:
                legend.setdefault(name, color)
                segment_height = count * plot_height / axis_max
                y -= segment_height
                bar = rectangle(x - bar_width / 2, y, bar_width, segment_height, color)
                SubElement(bar, "title").text = f"{year}, {name}: {count}"
        if total:
            label(x, y - 5, total, **{"text-anchor": "middle"})
        label(x, baseline + 20, year, **{"text-anchor": "middle"})

    if not peak:
        label(width / 2, 145, "No public commit contributions in this period", **{"text-anchor": "middle"})

    legend_top = 275
    column_width = (width - 50) / legend_columns
    for index, (name, color) in enumerate(legend.items()):
        row, column = divmod(index, legend_columns)
        x = 25 + column * column_width
        y = legend_top + 24 * row
        rectangle(x, y - 9, 10, 10, color)
        label(x + 17, y, name)

    return tostring(svg, encoding="unicode") + "\n"
