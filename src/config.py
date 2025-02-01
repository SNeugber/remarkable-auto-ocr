from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class _Config:
    GoogleAPIKey: str
    RemarkableIPAddress: str
    SSHKeyPath: str
    GitRepoPath: Path | None = None
    GDriveFolderPath: Path | None = None


def _load():
    path = Path.home() / "env.toml"
    data = tomllib.load(path.open("rb"))
    return _Config(**data["remarkable-auto-ocr-app"])


Config = _load()
