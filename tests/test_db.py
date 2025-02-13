from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from rao import db
from rao.file_processing_config import ProcessingConfig
from rao.models import Base, Metadata, RemarkableFile


@patch("rao.db.Base")
@patch("rao.db.Config")
def test_get_engine(mock_config: MagicMock, mock_base: MagicMock, tmp_path: Path):
    # Given
    db_dir = tmp_path / "db_dir"
    db_dir.mkdir()
    mock_config.db_data_dir = db_dir

    # When
    engine = db.get_engine()

    # Then
    assert engine.url.database == str(tmp_path / "db_dir/db.sqlite")
    mock_base.metadata.create_all.assert_called_once_with(engine)


def test_out_of_sync_files():
    # Mock the engine and session objects
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    file1 = RemarkableFile(
        uuid="uuid1",
        name="file1",
        last_modified=datetime.now(),
        type="a",
        parent_uuid=None,
        path=Path("file1"),
        other_files=[],
    )
    file2 = RemarkableFile(
        uuid="uuid2",
        name="file2",
        last_modified=datetime.now(),
        type="a",
        parent_uuid=None,
        path=Path("file2"),
        other_files=[],
    )

    config1 = ProcessingConfig(pdf_only=True, force_reprocess=False, prompt=None)
    config2 = ProcessingConfig(pdf_only=True, force_reprocess=True, prompt=None)

    file_configs = {file1: config1, file2: config2}

    meta1 = Metadata(
        uuid="uuid1", last_modified=datetime.now() - timedelta(days=1), prompt_hash=123
    )
    session.add(meta1)
    session.commit()

    out_of_sync = db.out_of_sync_files(file_configs, engine)
    assert len(out_of_sync) == 2
    assert any(f.uuid == "uuid1" for f in out_of_sync)
    assert any(f.uuid == "uuid2" for f in out_of_sync)

    Base.metadata.drop_all(engine)  # Cleanup
