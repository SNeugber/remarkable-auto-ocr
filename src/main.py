from pathlib import Path
import time
from loguru import logger
import db
import remarkable
from config import Config

logger.add("/var/log/my_python_service.log", level="INFO")


def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        session = remarkable.open_connection()
        files = remarkable.get_files(session)
        print(files)
        to_update = db.out_of_sync_files(files, engine)
        print(to_update)
        # files = files_to_process(engine)
        # parsed = parse_files(files)
        # uploaded = upload_to_gdrive(parsed)
        # mark_files_parsed(db, uploaded)
        time.sleep(120)


def main():
    run()


if __name__ == "__main__":
    main()
