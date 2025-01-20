import time
from loguru import logger
import db
import remarkable

logger.add("/var/log/my_python_service.log", level="INFO")


def run():
    logger.info("Service is running...")
    engine = db.get_engine()
    while True:
        session = remarkable.open_connection(host="192.168.1.7")
        files = remarkable.get_files(session)
        print(files)
        _ = db.out_of_sync_files(files, engine)
        # files = files_to_process(engine)
        # parsed = parse_files(files)
        # uploaded = upload_to_gdrive(parsed)
        # mark_files_parsed(db, uploaded)
        time.sleep(120)


def main():
    run()


if __name__ == "__main__":
    main()
