from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import Metadata, Base, RemarkableFile


def get_engine() -> Engine:
    db_dir = Path("./data")
    db_dir.mkdir(exist_ok=True)
    engine = create_engine("sqlite:///data/db.sqlite", echo=True)
    Base.metadata.create_all(engine)
    return engine


def out_of_sync_files(
    files: list[RemarkableFile], engine: Engine
) -> list[RemarkableFile]:
    Session = sessionmaker(bind=engine)
    session = Session()
    existing = session.query(Metadata).all()
    to_update = []
    meta_by_uuid = {meta.uuid: meta for meta in existing}
    for file in files:
        if file.type != "DocumentType":
            continue
        if (
            file.uuid not in meta_by_uuid
            or meta_by_uuid[file.uuid].last_modified < file.last_modified
        ):
            to_update.append(file)
    return to_update


def upsert_files(engine: Engine, files: list[tuple[str, dict]]):
    Session = sessionmaker(bind=engine)
    session = Session()

    for file_name, file_contents in files:
        metadata = Metadata(
            id=file_name,
            created_time=datetime.fromtimestamp(file_contents["createdTime"]),
            last_modified=datetime.fromtimestamp(file_contents["lastModified"]),
            parent_id=file_contents["parent"],
            type=file_contents["type"],
            visible_name=file_contents["visibleName"],
        )
        session.add(metadata)

    session.commit()
    session.close()
