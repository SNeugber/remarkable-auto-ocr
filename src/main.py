import itertools
import time
from loguru import logger
import db
import remarkable
import doc_parsing as dp
import file_sync as fs

logger.add("./logs/debug.log", level="INFO")


@logger.catch
def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        with remarkable.connect() as session:
            files = remarkable.get_files(session)
            files_to_update = db.out_of_sync_files(files, engine)
            pages = [remarkable.render_pages(session, file) for file in files_to_update]
            pages = list(itertools.chain.from_iterable(pages))[:2]

        pages_to_render = db.out_of_sync_pages(pages, engine)
        md_files = {page: dp.pdf2md(page.data) for page in pages_to_render}
        saved = fs.save(files, md_files)
        db.mark_as_synced(saved, engine)
        time.sleep(120)


def main():
    run()


if __name__ == "__main__":
    main()
