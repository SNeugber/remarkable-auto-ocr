# tests/test_db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.rao import db
from src.rao.models import Base, Metadata, ProcessingConfig, RemarkableFile


def test_get_engine():
    engine = db.get_engine()
    assert engine.url.database == "data/db.sqlite"
    Base.metadata.drop_all(engine)  # Cleanup


def test_out_of_sync_files():
    # Mock the engine and session objects
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    file1 = RemarkableFile(uuid="uuid1", last_modified=1000)
    file2 = RemarkableFile(uuid="uuid2", last_modified=2000)

    config1 = ProcessingConfig(force_reprocess=False, prompt_hash=123)
    config2 = ProcessingConfig(force_reprocess=True, prompt_hash=456)

    file_configs = {file1: config1, file2: config2}

    meta1 = Metadata(uuid="uuid1", last_modified=500, prompt_hash=123)
    session.add(meta1)
    session.commit()

    out_of_sync = db.out_of_sync_files(file_configs, engine)
    assert len(out_of_sync) == 2
    assert any(f.uuid == "uuid1" for f in out_of_sync)
    assert any(f.uuid == "uuid2" for f in out_of_sync)

    Base.metadata.drop_all(engine)  # Cleanup
