from datetime import datetime
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import toml

from rao.file_processing_config import ProcessingConfig
from rao.models import Metadata, RemarkableFile


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

    with mock.patch("rao.config.CONFIG_PATH", new=config_path):
        from rao.config import Config

        Config.reload()
        yield Config


@pytest.fixture
def files():
    def build(n: int):
        return [
            RemarkableFile(
                uuid=f"uuid{i}",
                name=f"file{i}",
                last_modified=datetime.now(),
                type="document",
                parent_uuid=None,
                path=Path(f"file{i}"),
                other_files=[],
            )
            for i in range(n)
        ]

    return build


@pytest.fixture
def files_and_configs(files):
    def build(n: int):
        _files = files(n)
        configs = [
            ProcessingConfig(pdf_only=False, force_reprocess=False, prompt=f"{i}")
            for i in range(n)
        ]
        meta_data = [
            Metadata(
                uuid=_files[i].uuid,
                last_modified=_files[i].last_modified,
                prompt_hash=configs[i].prompt_hash,
            )
            for i in range(n)
        ]
        return (_files, configs, meta_data)

    return build
