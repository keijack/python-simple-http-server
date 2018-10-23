# -*- coding: utf-8 -*-
import sys
import logging

__LOG_LEVEL_ = "INFO"


def set_level(level):
    global __LOG_LEVEL_
    lv = level.upper()
    if lv in ("DEBUG", "INFO", "WARN", "ERROR"):
        _logger_ = getLogger("Logger", "INFO")
        _logger_.info("global logger set to %s" % lv)
        __LOG_LEVEL_ = lv


def getLogger(tag="simple_http_server", level=None):
    logger = logging.getLogger(tag)

    _formatter_ = logging.Formatter(fmt='[%(asctime)s]-[%(name)s]-[line:%(lineno)d] -%(levelname)-4s: %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
    screen_handler = logging.StreamHandler(sys.stdout)
    screen_handler.setFormatter(_formatter_)
    if level is not None:
        logger.setLevel(level.upper())
        screen_handler.setLevel(level.upper())
    else:
        logger.setLevel(__LOG_LEVEL_)
        screen_handler.setLevel(__LOG_LEVEL_)

    logger.addHandler(screen_handler)
    return logger
