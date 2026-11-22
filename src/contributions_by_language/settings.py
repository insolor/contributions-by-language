from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_config import SettingsConfig, SettingsModel
from pydantic_settings import CliPositionalArg, CliSettingsSource

from .chart import ChartType, GroupBy
from .palette import DEFAULT_MAX_COLORS, MAX_PALETTE_COLORS

DEFAULT_YEARS = 5


class Settings(SettingsModel):
    """Generate an SVG chart of GitHub commits."""

    model_config = SettingsConfig(
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_avoid_json=True,
        env_prefix="CONTRIBUTIONS_BY_LANGUAGE_",
    )

    login: CliPositionalArg[str | None] = Field(None, description="GitHub username.")
    config: Path | None = Field(None, description="TOML, YAML or JSON settings file.")
    all_time: bool = Field(False, description="Include all available commit history.")
    years: int | None = Field(
        None,
        ge=1,
        description=f"Calendar years including the current UTC year. Default is {DEFAULT_YEARS}.",
    )
    output: Path = Field(Path("contributions.svg"), description="Output SVG path.")
    refresh_cache: bool = Field(
        False, description="Fetch closed months again and update the cache."
    )
    theme: Literal["light", "dark"] = Field("light", description="Chart theme.")
    chart_type: ChartType = Field("bar", description="Chart style: bar or line.")
    group_by: GroupBy = Field(
        "year", description="Bar interval: year, quarter or month."
    )
    max_colors: int = Field(
        DEFAULT_MAX_COLORS,
        ge=2,
        le=MAX_PALETTE_COLORS,
        description="Maximum chart colors, including grouped categories.",
    )
    force_other_languages: list[str] = Field(
        default_factory=list,
        description="Languages always grouped under Other languages.",
    )
    show_legend_counts: bool = Field(
        True, description="Show commit counts in the chart legend."
    )
    show_other_languages: bool = Field(
        True, description="Show the Other languages group."
    )

    @model_validator(mode="after")
    def validate_period(self) -> Settings:
        if self.all_time and self.years is not None:
            raise ValueError("all_time and years are mutually exclusive")
        return self


def load_settings(args: list[str]) -> Settings:
    overrides = CliSettingsSource(Settings, cli_parse_args=args)()
    if overrides.get("all_time") and "years" in overrides:
        raise ValueError("--all-time and --years are mutually exclusive")
    if overrides.get("all_time"):
        overrides["years"] = None
    elif "years" in overrides:
        overrides["all_time"] = False

    config_arg = overrides.pop("config", None)
    path = Path(config_arg).expanduser() if config_arg else Path("contributions.toml")
    if path.suffix not in {".toml", ".yaml", ".yml", ".json"}:
        raise ValueError(f"Unsupported settings file format: {path.suffix}")
    if config_arg and not path.is_file():
        raise ValueError(f"Settings file not found: {path}")

    class FileSettings(Settings):
        model_config = SettingsConfig(config_file=path)

    return FileSettings(**overrides)
