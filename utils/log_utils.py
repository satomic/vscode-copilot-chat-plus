import os
import logging
from datetime import datetime
from utils.time_utils import current_time
from config import is_debug_enabled

# Get whether to enable debug
debug = is_debug_enabled()

log_format = '%(asctime)s - [%(levelname)s] - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)


def configure_logger(log_path=None, with_date_folder=True):
    if log_path is None:
        log_path = os.environ.get('LOG_PATH', 'logs')

    if with_date_folder:
        log_path = os.path.join(log_path, current_time()[:10])

    if not os.path.exists(log_path):
        os.makedirs(log_path)

    log_file_name = f"{log_path}/{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file_name, mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger(__name__)
    # 无论是否为调试模式，始终将日志级别设置为 INFO
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    return logger


logger = configure_logger(log_path="logs", with_date_folder=False)
logger.info('-----------------Starting-----------------')


if __name__ == '__main__':
    logger = configure_logger()
    logger.info("test")
    logger.debug("test")
    logger.warning("test")
    logger.error("test")