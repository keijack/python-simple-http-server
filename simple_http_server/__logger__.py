# -*- coding: utf-8 -*-
import sys
import logging
from threading import Lock

__LOG_LEVEL_ = "INFO"
__loggers_ = {}
__loggers_lock = Lock()

__formatter_ = logging.Formatter(
    fmt='[%(asctime)s]-[%(name)s]-[line:%(lineno)d] -%(levelname)-4s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


def set_level(level):
    global __LOG_LEVEL_
    assert level is not None and level.upper() in ("DEBUG", "INFO", "WARN", "ERROR")
    lv = level.upper()

    _logger_ = getLogger("simple_http_server.__logger__", "INFO")
    _logger_.info("global logger level set to %s" % lv)
    __LOG_LEVEL_ = lv


def getLogger(tag="simple_http_server.__not_set__", level=None):
    assert level is None or level.upper() in ("DEBUG", "INFO", "WARN", "ERROR")
    lv = level.upper() if level is not None else __LOG_LEVEL_
    if tag not in __loggers_:
        with __loggers_lock:
            logger = logging.getLogger(tag)

            screen_handler = logging.StreamHandler(sys.stdout)
            screen_handler.setFormatter(__formatter_)
            logger.setLevel(lv)
            screen_handler.setLevel(lv)

            logger.addHandler(screen_handler)

            __loggers_[tag] = logger
    else:
        logger = __loggers_[tag]

    if level is not None:
        logger.setLevel(lv)

    return logger
