from collections import Counter
from xml.etree.ElementTree import fromstring

from contributions_by_language.cache import MonthCache, MonthRecord
from contributions_by_language.chart import render_svg
from contributions_by_language.settings import load_settings


def main() -> None:
    settings = load_settings([])
    if not settings.login:
        raise SystemExit("Set login in contributions.toml")

    cache = MonthCache(settings.login)
    monthly = {}
    for path in sorted(cache.directory.glob("*.jsonl")):
        for line in path.read_bytes().splitlines():
            record = MonthRecord.model_validate_json(line, strict=True)
            monthly[record.month] = Counter(record.counts)

    svg = render_svg(
        monthly,
        settings.login,
        theme=settings.theme,
        max_colors=settings.max_colors,
        force_other_languages=settings.force_other_languages,
        show_legend_counts=settings.show_legend_counts,
        show_other_languages=settings.show_other_languages,
        group_by=settings.group_by,
        chart_type=settings.chart_type,
    )
    assert fromstring(svg).tag == "{http://www.w3.org/2000/svg}svg"


if __name__ == "__main__":
    main()
