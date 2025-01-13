import time
from loguru import logger

logger.add('/var/log/my_python_service.log', level="INFO")

def main():
    while True:
        logger.info("Service is running...")
        time.sleep(60)

if __name__ == "__main__":
    main()