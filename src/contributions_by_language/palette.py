import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files


@dataclass(frozen=True)
class Palette:
    """Define a chart theme's styling and language color preferences."""

    background: str
    foreground: str
    grid: str
    no_language: str
    other_languages: str
    languages: tuple[str, ...]
    use_linguist: bool = False


LIGHT = Palette(
    background="#f8fafc",
    foreground="#1e293b",
    grid="#cbd5e1",
    no_language="#737373",
    other_languages="#657d90",
    use_linguist=True,
    languages=(
        "#0047ab",
        "#e88400",
        "#007a4d",
        "#f04c9b",
        "#5d2387",
        "#00a6c6",
        "#bb1900",
        "#63401f",
        "#147d89",
        "#913b57",
        "#a1844b",
        "#91a621",
    ),
)

DARK = Palette(
    background="#171717",
    foreground="#e6e6e6",
    grid="#363636",
    no_language="#737373",
    other_languages="#657d90",
    use_linguist=True,
    languages=(
        "#0047ab",
        "#e88400",
        "#007a4d",
        "#a16ba8",
        "#5d2387",
        "#619eb8",
        "#b56348",
        "#63401f",
        "#147d89",
        "#913b57",
        "#a1844b",
        "#91a621",
    ),
)

PALETTES = {"light": LIGHT, "dark": DARK}
DEFAULT_MAX_COLORS = 6
MAX_PALETTE_COLORS = min(len(palette.languages) for palette in PALETTES.values())


@cache
def linguist_colors() -> dict[str, str]:
    """Load the bundled Linguist colors indexed by case-folded name."""
    data = files("contributions_by_language").joinpath("linguist_colors.json")
    colors = json.loads(data.read_text(encoding="utf-8"))
    return {name.casefold(): color for name, color in colors.items()}
