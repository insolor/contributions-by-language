from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    background: str
    foreground: str
    grid: str
    no_language: str
    languages: tuple[str, ...]


LIGHT = Palette(
    background="#f8fafc",
    foreground="#1e293b",
    grid="#cbd5e1",
    no_language="#737373",
    languages=(
        "#0047ab", "#e88400", "#007a4d", "#f04c9b",
        "#5d2387", "#00a6c6", "#bb1900", "#63401f",
        "#147d89", "#913b57", "#a1844b", "#91a621",
    ),
)

DARK = Palette(
    background="#171717",
    foreground="#e6e6e6",
    grid="#363636",
    no_language=LIGHT.no_language,
    languages=LIGHT.languages,
)

PALETTES = {"light": LIGHT, "dark": DARK}
DEFAULT_MAX_COLORS = 6
MAX_PALETTE_COLORS = min(len(palette.languages) for palette in PALETTES.values())
