from collections.abc import Iterable

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import DB_CACHE_PATH
from .file_processing_config import ProcessingConfig
from .models import Base, Metadata, Page, RemarkableFile, RemarkablePage


def get_engine() -> Engine:
    engine = create_engine(f"sqlite:///{DB_CACHE_PATH}", echo=True)
    Base.metadata.create_all(engine)
    return engine


def out_of_sync_files(
    file_configs: dict[RemarkableFile, ProcessingConfig], engine: Engine
) -> list[RemarkableFile]:
    logger.info("Fetching files to process from DB")
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
    logger.info(f"Got {len(files_to_update)} out of sync files from DB")
    return files_to_update


def out_of_sync_pages(
    pages: Iterable[RemarkablePage],
    file_configs: dict[RemarkableFile, ProcessingConfig],
    engine: Engine,
) -> list[RemarkablePage]:
    logger.info("Fetching pages that need updating from DB")
    page_ids = [page.uuid for page in pages]
    Session = sessionmaker(bind=engine)
    session = Session()
    db_pages = session.query(Page).filter(Page.uuid.in_(page_ids)).all()
    to_update = {
        page
        for page in pages
        if page.parent in file_configs and file_configs[page.parent].force_reprocess
    }
    for page in pages:
        db_page = next((p for p in db_pages if p.uuid == page.uuid), None)
        if db_page is None or db_page.hash != page.hash:
            to_update.add(page)
    logger.info(f"Got {len(to_update)} out of sync pages from DB")
    return list(to_update)


def mark_as_synced(
    saved: dict[RemarkableFile, list[RemarkablePage]],
    file_configs: dict[RemarkableFile, ProcessingConfig],
    engine: Engine,
):
    file_uuids = [file.uuid for file in saved.keys()]
    page_uuids = [page.uuid for pages in saved.values() for page in pages]

    logger.info(f"Updating {len(file_uuids)} files and {len(page_uuids)} pages in DB")
    if len(saved) == 0:
        return
    Session = sessionmaker(bind=engine)
    session = Session()

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
