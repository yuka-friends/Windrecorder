import logging
import os
from logging.handlers import RotatingFileHandler

logger = None


def get_logger(name, log_name="wr.log"):
    global logger
    if logger is not None:
        return logger

    log_dir = "cache\\logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(levelname)s - %(message)s")

    # 创建一个滚动文件处理器，每个日志文件最大大小为5M，保存5个旧日志文件
    rf_handler = RotatingFileHandler(
        os.path.join(log_dir, log_name),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    # rf_handler = TimedRotatingFileHandler(os.path.join(log_dir, log_name), when="d", interval=1, backupCount=7)
    # rf_handler.suffix = "%Y-%m-%d_%H-%M-%S.log"  # 设置历史文件 后缀
    rf_handler.setFormatter(formatter)
    logger.addHandler(rf_handler)

    if os.path.exists("DEBUGMODE.txt"):
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


"""
usage:

from windrecorder.logger import get_logger

logger = get_logger(__name__)
"""
