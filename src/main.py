import time
from loguru import logger
import db
import remarkable
from doc_parsing import pdf2md

logger.add("./logs/debug.log", level="INFO")

@logger.catch
def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        session = remarkable.open_connection()
        files = remarkable.get_files(session)
        to_update = db.out_of_sync_files(files, engine)
        for file in to_update:
            pdf = remarkable.render_pdf(file, session)
            md = pdf2md(pdf)
            print(len(pdf))
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
