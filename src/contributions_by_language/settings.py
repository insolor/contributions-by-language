from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_config import SettingsConfig, SettingsModel
from pydantic_settings import CliPositionalArg, CliSettingsSource

from .palette import DEFAULT_MAX_COLORS, MAX_PALETTE_COLORS


class Settings(SettingsModel):
    """Generate an SVG of yearly GitHub commits."""

    model_config = SettingsConfig(
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_avoid_json=True,
        env_prefix="CONTRIBUTIONS_BY_LANGUAGE_",
    )

    login: CliPositionalArg[str | None] = Field(None, description="GitHub username.")
    config: Path | None = Field(None, description="TOML, YAML or JSON settings file.")
    all_time: bool = Field(False, description="Include all available commit history.")
    months: int | None = Field(
        None, ge=1, le=60,
        description="Calendar months including the current UTC month. Default is 12.",
    )
    output: Path = Field(Path("contributions.svg"), description="Output SVG path.")
    refresh_cache: bool = Field(False, description="Fetch closed months again and update the cache.")
    theme: Literal["light", "dark"] = Field("light", description="Chart theme.")
    max_colors: int = Field(
        DEFAULT_MAX_COLORS, ge=2, le=MAX_PALETTE_COLORS,
        description="Maximum chart colors, including grouped categories.",
    )
    force_other_languages: list[str] = Field(
        default_factory=list, description="Languages always grouped under Other languages.",
    )

    @model_validator(mode="after")
    def validate_period(self) -> Settings:
        if self.all_time and self.months is not None:
            raise ValueError("all_time and months are mutually exclusive")
        return self


def load_settings(args: list[str]) -> Settings:
    overrides = CliSettingsSource(Settings, cli_parse_args=args)()
    if overrides.get("all_time") and "months" in overrides:
        raise ValueError("--all-time and --months are mutually exclusive")
    if overrides.get("all_time"):
        overrides["months"] = None
    elif "months" in overrides:
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
