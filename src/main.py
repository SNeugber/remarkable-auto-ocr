import itertools
import time
from loguru import logger
import db
import remarkable
import doc_parsing as dp
import file_sync as fs
from config import Config
import file_processing_config as fpc

logger.add("./logs/debug.log", level="INFO")


@logger.catch
def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        with remarkable.connect() as session:
            if session is None:
                logger.warning("Could not connect to Remarkable.")
                time.sleep(Config.check_interval)
                continue
            files = remarkable.get_files(session)
            file_configs = fpc.get_configs_for_files(files)
            files_to_process = list(file_configs.keys())
            files_to_update = db.out_of_sync_files(files_to_process, engine)[:1]
            pages = [remarkable.render_pages(session, file) for file in files_to_update]

        all_pages = list(itertools.chain.from_iterable(pages))
        out_of_sync = db.out_of_sync_pages(all_pages, engine)
        rendered, failed = dp.pages_to_md(out_of_sync, file_configs)
        saved = fs.save(all_pages, rendered)
        saved = {
            file: pages
            for file, pages in saved.items()
            if not any([p for p in pages if p in failed])
        }
        db.mark_as_synced(saved, engine)
        time.sleep(Config.check_interval)


def main():
    run()


if __name__ == "__main__":
    main()
