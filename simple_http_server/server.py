# -*- coding: utf-8 -*-

import os
import simple_http_server.http_server as http_server
from simple_http_server import request_map
from simple_http_server import StaticFile
from simple_http_server.__logger__ import getLogger
import threading


__logger = getLogger("simple_http_server.server")
__lock = threading.Lock()
__server = None


def start(host="", port=9090):
    with __lock:
        global __server
        __server = http_server.SimpleDispatcherHttpServer((host, port))

    from simple_http_server import _get_filters
    __filters = _get_filters()
    # filter configuration
    for ft in __filters:
        __server.map_filter(ft["url_pattern"], ft["func"])

    from simple_http_server import _get_request_mappings
    __request_mappings = _get_request_mappings()
    # request mapping
    for ctr in __request_mappings:
        __server.map_request(ctr["url"], ctr["func"], ctr["method"])

    # start the server
    __server.start()


def stop():
    with __lock:
        global __server
        if __server is not None:
            __logger.info("shutting down server...")
            __server.shutdown()
            __server = None


@request_map("/favicon.ico")
def _favicon():
    root = os.path.dirname(os.path.abspath(__file__))
    return StaticFile("%s/favicon.ico" % root, "image/x-icon")
