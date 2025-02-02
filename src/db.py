from collections.abc import Iterable
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from models import Metadata, Base, Page, RemarkableFile, RemarkablePage


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
        if (
            file.uuid not in meta_by_uuid
            or meta_by_uuid[file.uuid].last_modified < file.last_modified
        ):
            to_update.append(file)
    return to_update


def out_of_sync_pages(
    pages: Iterable[RemarkablePage], engine: Engine
) -> list[RemarkablePage]:
    page_ids = [page.uuid for page in pages]
    Session = sessionmaker(bind=engine)
    session = Session()
    db_pages = session.query(Page).filter(Page.uuid.in_(page_ids)).all()
    to_update = []
    for page in pages:
        db_page = next((p for p in db_pages if p.uuid == page.uuid), None)
        if db_page is None or db_page.hash != page.hash:
            to_update.append(page)
    return to_update


def mark_as_synced(saved: dict[RemarkableFile, list[RemarkablePage]], engine: Engine):
    if len(saved) == 0:
        return
    Session = sessionmaker(bind=engine)
    session = Session()

    for file, pages in saved.items():
        metadata = Metadata(
            uuid=file.uuid,
            visible_name=file.name,
            last_modified=file.last_modified,
            parent_uuid=file.parent_uuid,
            type=file.type,
        )
        metadata.pages.extend([Page(uuid=page.uuid, hash=page.hash) for page in pages])
        session.add(metadata)
    session.commit()
    session.close()
