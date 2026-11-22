from collections import Counter
from collections.abc import Sequence
from datetime import date

from .chart_data import prepare_chart_data
from .palette import DEFAULT_MAX_COLORS, PALETTES
from .svg_chart import ChartType, GroupBy, SvgChartRenderer


def render_svg_chart(
    monthly: dict[date, Counter[str]],
    login: str,
    *,
    title: str | None = None,
    theme: str = "light",
    max_colors: int = DEFAULT_MAX_COLORS,
    force_other_languages: Sequence[str] = (),
    show_legend_counts: bool = True,
    show_other_languages: bool = True,
    group_by: GroupBy = "year",
    chart_type: ChartType = "bar",
) -> str:
    if title is None:
        frequency = {"year": "Yearly", "quarter": "Quarterly", "month": "Monthly"}
        title = f"{frequency[group_by]} GitHub commits by language · @{login}"
    palette = PALETTES[theme]
    data = prepare_chart_data(
        monthly,
        title,
        palette,
        max_colors=max_colors,
        force_other_languages=force_other_languages,
        show_other_languages=show_other_languages,
        group_by=group_by,
        chart_type=chart_type,
    )
    return SvgChartRenderer(palette).render(
        data,
        show_legend_counts=show_legend_counts,
        group_by=group_by,
        chart_type=chart_type,
    )
