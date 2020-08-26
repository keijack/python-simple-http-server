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


def _is_match(string="", regx=r""):
    if not regx:
        return True
    pattern = re.compile(regx)
    match = pattern.match(string)
    return True if match else False


def _to_module_name(fpath="", regx=r""):
    fname, fext = os.path.splitext(fpath)

    if fext != ".py":
        return
    mname = fname.replace(os.path.sep, '.')
    if _is_match(fpath, regx) or _is_match(fname, regx) or _is_match(mname, regx):
        return mname


def _load_all_modules(work_dir, pkg, regx):
    abs_folder = work_dir + "/" + pkg
    all_files = os.listdir(abs_folder)
    modules = []
    folders = []
    for f in all_files:
        if os.path.isfile(os.path.join(abs_folder, f)):
            mname = _to_module_name(os.path.join(pkg, f), regx)
            if mname:
                modules.append(mname)
        elif f != "__pycache__":
            folders.append(os.path.join(pkg, f))

    for folder in folders:
        modules += _load_all_modules(work_dir, folder, regx)
    return modules


def _import_module(mname):
    try:
        importlib.import_module(mname)
    except:
        __logger.warn("Import moudle [%s] error!" % mname)


def scan(base_dir="", regx=r""):
    ft = inspect.currentframe()
    fts = inspect.getouterframes(ft)
    entrance = fts[-1]
    work_dir = os.path.dirname(inspect.getabsfile(entrance[0]))
    modules = _load_all_modules(work_dir, base_dir, regx)

    for mname in modules:
        __logger.info("Import controllers from module: %s" % mname)
        _import_module(mname)


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
