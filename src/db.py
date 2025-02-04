from collections.abc import Iterable
from pathlib import Path
from file_processing_config import ProcessingConfig
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
    file_configs: dict[RemarkableFile, ProcessingConfig], engine: Engine
) -> list[RemarkableFile]:
    files_to_update = [
        file for file, config in file_configs.items() if config.force_reprocess
    ]
    files_to_check_sync = [
        file for file, config in file_configs.items() if not config.force_reprocess
    ]

    Session = sessionmaker(bind=engine)
    session = Session()
    existing = (
        session.query(Metadata)
        .filter(Metadata.uuid.in_([f.uuid for f in files_to_check_sync]))
        .all()
    )
    meta_by_uuid = {meta.uuid: meta for meta in existing}
    for file in files_to_check_sync:
        if (
            file.uuid not in meta_by_uuid
            or meta_by_uuid[file.uuid].last_modified < file.last_modified
            or (meta_by_uuid[file.uuid].prompt_hash != file_configs[file].prompt_hash)
        ):
            files_to_update.append(file)
    return files_to_update


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


def mark_as_synced(
    saved: dict[RemarkableFile, list[RemarkablePage]],
    file_configs: dict[RemarkableFile, ProcessingConfig],
    engine: Engine,
):
    if len(saved) == 0:
        return
    Session = sessionmaker(bind=engine)
    session = Session()

    file_uuids = [file.uuid for file in saved.keys()]
    page_uuids = [page.uuid for pages in saved.values() for page in pages]
    existing_files = session.query(Metadata).filter(Metadata.uuid.in_(file_uuids)).all()
    existing_files = {f.uuid: f for f in existing_files}
    existing_pages = session.query(Page).filter(Page.uuid.in_(page_uuids)).all()
    existing_pages = {p.uuid: p for p in existing_pages}

    for file, pages in saved.items():
        if file.uuid in existing_files:
            metadata = existing_files[file.uuid]
        else:
            metadata = Metadata(uuid=file.uuid)
        metadata.visible_name = file.name
        metadata.last_modified = file.last_modified
        metadata.parent_uuid = file.parent_uuid
        metadata.type = file.type
        metadata.prompt_hash = file_configs[file].prompt_hash
        new_pages = []
        for page in pages:
            if page.uuid in existing_pages:
                orm_page = existing_pages[page.uuid]
                orm_page.hash = page.hash
            else:
                new_pages.append(Page(uuid=page.uuid, hash=page.hash))
        if new_pages:
            metadata.pages.extend(new_pages)
        if file.uuid not in existing_files:
            session.add(metadata)
    session.commit()
    session.close()
