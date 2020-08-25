# -*- coding: utf-8 -*-

import os
import simple_http_server.http_server as http_server
from simple_http_server import request_map
from simple_http_server import StaticFile
from simple_http_server.logger import get_logger
import threading
import inspect
import importlib
import re


__logger = get_logger("simple_http_server.server")
__lock = threading.Lock()
__server = None


def _load_all_files(work_dir, pkg):
    abs_folder = work_dir + "/" + pkg
    files = [os.path.join(pkg, f) for f in os.listdir(abs_folder) if f.endswith(".py")]
    folders = [os.path.join(pkg, f) for f in os.listdir(abs_folder) if os.path.isdir(os.path.join(abs_folder, f)) and f != "__pycache__"]
    for folder in folders:
        files += _load_all_files(work_dir, folder)
    return files


def _is_match(regx=r"", string=""):
    if not regx:
        return True
    pattern = re.compile(regx)
    match = pattern.match(string)
    if match:
        return True
    else:
        return False


def scan(base_dir="", regx=r""):
    ft = inspect.currentframe()
    fts = inspect.getouterframes(ft)
    entrance = fts[-1]
    work_dir = os.path.dirname(inspect.getabsfile(entrance[0]))
    files = _load_all_files(work_dir, base_dir)
    
    for f in files:
        fname = os.path.splitext(f)[0]
        mname = fname.replace(os.path.sep, '.')
        if _is_match(regx, fname) or _is_match(regx, mname):
            __logger.info("import controllers from module: %s" % mname)
            importlib.import_module(mname)


def start(host="", port=9090, resources={}):
    with __lock:
        global __server
        if __server is not None:
            __server.shutdown()
        __server = http_server.SimpleDispatcherHttpServer((host, port), resources=resources)

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
