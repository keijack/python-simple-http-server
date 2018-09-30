# -*- coding: utf-8 -*-

from simple_http_server.http_server import SimpleDispatcherHttpServer
from simple_http_server.__logger__ import getLogger

__logger = getLogger("server")

__request_mappings = []
__filters = []

__server = None


def request_map(url, method=""):
    def map(ctrl_fun):
        __logger.debug("maping url %s to function %s " % (url, str(ctrl_fun)))
        __request_mappings.append({
            "url": url,
            "method": method,
            "func": ctrl_fun
        })
    return map


def filter(pattern):
    def map(filter_fun):
        __filters.append({"url_pattern": pattern, "func": filter_fun})
    return map


def start(host="", port=9090):
    global __server
    __server = SimpleDispatcherHttpServer((host, port))

    # filter configuration
    for ft in __filters:
        __server.map_filter(ft["url_pattern"], ft["func"])

    # request mapping
    for ctr in __request_mappings:
        __server.map_request(ctr["url"], ctr["func"], ctr["method"])

    # start the server
    __server.start()


def stop():
    global __server
    if __server is not None:
        __server.shutdown()
        __server = None
