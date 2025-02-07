import itertools
import time

from loguru import logger

from rao import db, remarkable
from rao import doc_parsing as dp
from rao import file_processing_config as fpc
from rao import file_sync as fs
from rao.config import Config

logger.add("./logs/debug.log", level="INFO")


@logger.catch
def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    check_interval = 0
    while True:
        time.sleep(check_interval)
        check_interval = Config.check_interval
        with remarkable.connect() as session:
            if session is None:
                logger.warning("Could not connect to Remarkable.")
                continue
            files = remarkable.get_files(session)
            file_configs = fpc.get_configs_for_files(files)
            files_to_update = db.out_of_sync_files(file_configs, engine)
            if not files_to_update:
                continue
            pages = [remarkable.render_pages(session, file) for file in files_to_update]

        all_pages = list(itertools.chain.from_iterable(pages))
        out_of_sync_pages = db.out_of_sync_pages(all_pages, engine)
        rendered, failed = dp.pages_to_md(out_of_sync_pages, file_configs)
        saved = fs.save(all_pages, rendered)
        saved = {
            file: pages
            for file, pages in saved.items()
            if not any([p in failed for p in pages])
        }
        db.mark_as_synced(saved, file_configs, engine)


def main():
    run()


if __name__ == "__main__":
    main()
