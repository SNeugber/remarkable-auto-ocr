from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from rao import db
from rao.file_processing_config import ProcessingConfig
from rao.models import Base, Metadata, RemarkableFile


@pytest.fixture
def files_and_configs():
    def build(n: int):
        files = [
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
        configs = [
            ProcessingConfig(pdf_only=False, force_reprocess=False, prompt=f"{i}")
            for i in range(n)
        ]
        meta_data = [
            Metadata(
                uuid=files[i].uuid,
                last_modified=files[i].last_modified,
                prompt_hash=configs[i].prompt_hash,
            )
            for i in range(n)
        ]
        return (files, configs, meta_data)

    return build


@patch("rao.db.Base")
@patch("rao.db.DB_CACHE_PATH")
def test_get_engine(
    mock_db_cache_path: MagicMock, mock_base: MagicMock, tmp_path: Path
):
    # Given
    db_dir = tmp_path / "db_dir"
    db_dir.mkdir()
    mock_db_cache_path.__str__.return_value = str(db_dir / "db.sqlite")

    # When
    engine = db.get_engine()

    # Then
    assert engine.url.database == str(db_dir / "db.sqlite")
    mock_base.metadata.create_all.assert_called_once_with(engine)


def test_out_of_sync_files(
    files_and_configs: Callable[[int], dict[RemarkableFile, ProcessingConfig]],
):
    # Given
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    files, configs, meta = files_and_configs(4)
    file_configs = {f: c for f, c in zip(files, configs)}

    meta[0].last_modified = datetime.now() - timedelta(days=1)  # 1: Out of date
    configs[1].force_reprocess = True  # 2: Force reprocess
    meta[2].prompt_hash = 123  # 3: Prompt hash changed

    session.add_all(meta)
    session.commit()

    # When
    out_of_sync = db.out_of_sync_files(file_configs, engine)

    # Then
    assert len(out_of_sync) == 3
    assert any(f.uuid == "uuid0" for f in out_of_sync)
    assert any(f.uuid == "uuid1" for f in out_of_sync)
    assert any(f.uuid == "uuid2" for f in out_of_sync)

    Base.metadata.drop_all(engine)  # Cleanup
