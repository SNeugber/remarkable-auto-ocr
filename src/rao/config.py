from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypeAlias

import tomllib
from loguru import logger

Seconds: TypeAlias = int

_DEFAULT_PROMPT = """Render this document as rmarkdown and ensure that tables are rendered as such where required."""
DB_CACHE_PATH = Path("/tmp/rao_db/db.sqlite")
CONFIG_PATH = Path("/data/config.toml")


class ConfigLoadError(Exception):
    pass


@dataclass()
class _Config:
    google_api_key: str = ""
    remarkable_ip_address: str = ""
    ssh_key_path: str = ""
    check_interval: Seconds = 120
    whitelist_path: str | None = None
    blacklist_path: str | None = None
    md_repo_path: str | None = None
    pdf_copy_path: str | None = None
    db_data_dir: str | None = None
    default_prompt: str = _DEFAULT_PROMPT
    model: str = "gemini-1.5-pro"
    backup_model: str = "gemini-1.5-flash"
    prompts_dir: str = "/data/prompts"
    render_path: str = "/data/renders"

    @classmethod
    def _load(cls):
        logger.info(f"Loading config from {CONFIG_PATH}")
        data = tomllib.load(CONFIG_PATH.open("rb"))
        return cls(**data["remarkable-auto-ocr-app"])

    def reload(self):
        try:
            new = self._load()
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Unable to load toml file: {e}")
            raise ConfigLoadError from e
        except FileNotFoundError as e:
            logger.error(f"Unable to load toml file: {e}")
            raise ConfigLoadError from e
        for key, value in asdict(new).items():
            setattr(self, key, value)


Config = _Config()
