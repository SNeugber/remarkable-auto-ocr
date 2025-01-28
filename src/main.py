import time
from loguru import logger
import db
import remarkable
import doc_parsing as dp

logger.add("./logs/debug.log", level="INFO")


@logger.catch
def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        with remarkable.connect() as session:
            files = remarkable.get_files(session)
            documents = [file for file in files if file.type == "Document"]
            files_to_update = db.out_of_sync_files(documents, engine)
            pdfs = {
                file.uuid: remarkable.pages_to_pdfs(session, file)
                for file in files_to_update
            }

        pdfs_to_render = db.out_of_sync_pages(pdfs, engine)
        md_files = {
            uuid: [dp.pdf2md(pdf) for pdf in pdfs]
            for uuid, pdfs in pdfs_to_render.items()
        }
        # todo: save somewhere...
        db.mark_rendered(files_to_update, pdfs, md_files)
        # parsed = [pdf2md(doc)]
        # files = files_to_process(engine)
        # parsed = parse_files(files)
        # uploaded = upload_to_gdrive(parsed)
        # mark_files_parsed(db, uploaded)
        time.sleep(120)


def main():
    run()


if __name__ == "__main__":
    main()
