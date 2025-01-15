import time
from loguru import logger

logger.add("/var/log/my_python_service.log", level="INFO")

def run(db):
    logger.info("Service is running...")
    while True:
        sync_remarkable(db)
        files = files_to_process(db)
        parsed = parse_files(files)
        uploaded = upload_to_gdrive(parsed)
        mark_files_parsed(db, uploaded)
        time.sleep(120)



def main():
    db = load_db()
    run(db)

if __name__ == "__main__":
    main()
