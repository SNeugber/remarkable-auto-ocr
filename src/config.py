from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import TypeAlias

Seconds: TypeAlias = int


@dataclass(frozen=True)
class _Config:
    google_api_key: str
    remarkable_ip_address: str
    ssh_key_path: str
    check_interval: Seconds = 120
    whitelist_path: str | None = None
    blacklist_path: str | None = None
    git_repo_path: str | None = None
    gdrive_folder_path: str | None = None
    default_prompt: str = "Turn this document into markdown. Do not include any text other than the raw markdown."
    prompts_dir: str = "./data/prompts"
    render_path: str = "./data/renders"


def _load():
    path = Path.home() / "env.toml"
    data = tomllib.load(path.open("rb"))
    return _Config(**data["remarkable-auto-ocr-app"])


Config = _load()
