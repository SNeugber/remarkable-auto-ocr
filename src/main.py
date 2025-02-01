import itertools
import time
from loguru import logger
import db
import remarkable
import doc_parsing as dp
import file_sync as fs
from config import Config

logger.add("./logs/debug.log", level="INFO")


@logger.catch
def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        with remarkable.connect() as session:
            if session is None:
                logger.warning("Could not connect to Remarkable.")
                time.sleep(Config.CheckInterval)
                continue
            files = remarkable.get_files(session)
            files_to_update = db.out_of_sync_files(files, engine)
            pages = [remarkable.render_pages(session, file) for file in files_to_update]
            pages = list(itertools.chain.from_iterable(pages))

        pages_to_render = db.out_of_sync_pages(pages, engine)
        md_files = {page: dp.pdf2md(page.data) for page in pages_to_render}
        failed = {page for page, md in md_files.items() if md is None}
        for page in failed:
            logger.error(f"Failed to convert {page.uuid} to markdown.")
        md_files = {page for page, md in md_files.items() if md is not None}
        saved = fs.save(files, md_files)
        db.mark_as_synced(saved, engine)
        time.sleep(Config.CheckInterval)


def main():
    run()


if __name__ == "__main__":
    main()
