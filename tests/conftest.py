from pathlib import Path
from typing import Any

import pytest
import toml


@pytest.fixture(autouse=True, scope="session")
def default_config(tmpdir_factory: Path) -> Any:
    config_path = tmpdir_factory.mktemp("data") / "config.toml"
    with open(config_path, "w") as f:
        toml.dump(
            {
                "remarkable-auto-ocr-app": {
                    "google_api_key": "test_key",
                    "remarkable_ip_address": "test_ip",
                    "ssh_key_path": "test_path",
                }
            },
            f,
        )
    from rao.config import Config

    Config.reload(config_path)
    yield Config
