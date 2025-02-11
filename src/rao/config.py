from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypeAlias

import tomllib
from loguru import logger

Seconds: TypeAlias = int

_DEFAULT_PROMPT = """Render this document as rmarkdown and ensure that tables are rendered as such where required."""


class ConfigLoadError(Exception):
    pass


@dataclass()
class _Config:
    google_api_key: str
    remarkable_ip_address: str
    ssh_key_path: str
    check_interval: Seconds = 120
    whitelist_path: str | None = None
    blacklist_path: str | None = None
    md_repo_path: str | None = None
    pdf_copy_path: str | None = None
    default_prompt: str = _DEFAULT_PROMPT
    model: str = "gemini-1.5-pro"
    backup_model: str = "gemini-1.5-flash"
    prompts_dir: str = "./data/prompts"
    render_path: str = "./data/renders"

    @classmethod
    def load(cls, path_override: Path | None = None):
        for path in (
            [
                Path.home() / "config.toml",
                Path(__file__).parent.parent.parent / "config.toml",
            ]
            if path_override is None
            else [path_override]
        ):
            if not path.exists():
                continue
            data = tomllib.load(path.open("rb"))
            return _Config(**data["remarkable-auto-ocr-app"])
        raise FileNotFoundError("Unable to find a config file, aborting")

    def reload(self, path_override: Path | None = None):
        try:
            new = self.load(path_override)
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Unable to load toml file: {e}")
            raise ConfigLoadError from e
        except FileNotFoundError as e:
            logger.error(f"Unable to load toml file: {e}")
            raise ConfigLoadError from e
        for key, value in asdict(new).items():
            setattr(self, key, value)


Config = _Config.load()  # Not catching, must succeed on startup!
