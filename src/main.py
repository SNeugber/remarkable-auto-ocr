import time
from loguru import logger
import db

logger.add("/var/log/my_python_service.log", level="INFO")


def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        files = files_to_process(engine)
        parsed = parse_files(files)
        uploaded = upload_to_gdrive(parsed)
        mark_files_parsed(db, uploaded)
        time.sleep(120)


def main():
    run()


if __name__ == "__main__":
    main()
