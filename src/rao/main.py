import itertools
import time
from pathlib import Path

import click
from loguru import logger
from sqlalchemy import Engine

from rao import db, remarkable
from rao import doc_parsing as dp
from rao import file_processing_config as fpc
from rao import file_sync as fs
from rao.config import Config


def run():
    logger.info("Service is running...")
    Config.reload()  # Must succeed on startup
    fs.load_db_file_from_backup()
    engine = db.get_engine()
    check_interval = 0
    while True:
        time.sleep(check_interval)
        check_interval = Config.check_interval
        try:
            run_once(engine)
        except Exception:
            logger.error(
                f"Failure during sync, trying again in {check_interval} seconds..."
            )


@logger.catch(reraise=True)
def run_once(engine: Engine):
    Config.reload()
    with remarkable.connect() as session:
        if session is None:
            return
        files = remarkable.get_files(session)
        file_configs = fpc.get_configs_for_files(files)
        files_to_update = db.out_of_sync_files(file_configs, engine)
        if not files_to_update:
            return
        pages = [remarkable.render_pages(session, file) for file in files_to_update]

    all_pages = list(itertools.chain.from_iterable(pages))
    out_of_sync_pages = db.out_of_sync_pages(all_pages, file_configs, engine)
    rendered, failed = dp.pages_to_md(out_of_sync_pages, file_configs)
    saved = fs.save(all_pages, rendered)
    saved = {
        file: pages
        for file, pages in saved.items()
        if not any([p in failed for p in pages])
    }
    db.mark_as_synced(saved, file_configs, engine)
    fs.save_db_file_to_backup()


@click.command()
def main():
    log_dir = Path("/data/logs")
    logger.add(log_dir / "debug.log", level="INFO")
    run()


if __name__ == "__main__":
    main()
