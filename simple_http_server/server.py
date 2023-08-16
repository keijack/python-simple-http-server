# -*- coding: utf-8 -*-

"""
Copyright (c) 2018 Keijack Wu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import threading
import inspect
import importlib
import re

from ssl import PROTOCOL_TLS_SERVER, SSLContext
from typing import Dict

from simple_http_server.http_server import HttpServer, ASGIProxy, WSGIProxy

from simple_http_server.app_conf import get_app_conf, AppConf
from .routing_server import RoutingServer
from simple_http_server._http_session_local_impl import LocalSessionFactory
from simple_http_server.logger import get_logger
from .app_conf import set_session_factory
from .basic_models import SessionFactory


_logger = get_logger("simple_http_server.server")
__lock = threading.Lock()
_server: HttpServer = None


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
    abs_folder = os.path.join(work_dir, pkg)
    if os.path.isfile(abs_folder):
        return [_to_module_name(pkg, regx)]
    if not os.path.exists(abs_folder):
        if abs_folder.endswith(".py"):
            _logger.warning(f"Cannot find package {pkg}, file [{abs_folder}] is not exist")
            return []
        if os.path.isfile(abs_folder + ".py"):
            return [_to_module_name(pkg + ".py", regx)]
        else:
            _logger.warning(f"Cannot find package {pkg}, file [{abs_folder}] is not exist")
            return []

    modules = []
    folders = []
    all_files = os.listdir(abs_folder)
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
    except Exception as e:
        _logger.warning(f"Import moudle [{mname}] error! {e}")


def scan(base_dir: str = "", regx: str = r"", project_dir: str = "") -> None:
    """
    Scan the given directory to import controllers. 

    - base_dir: the directory to scan. 
    - regx: only include the modules that match this regular expression, if absent, all files will be included.
    - project_dir: the project directory, default to the entrance file directory. 

    """
    if project_dir:
        work_dir = project_dir
    else:
        ft = inspect.currentframe()
        fts = inspect.getouterframes(ft)
        entrance = fts[-1]
        work_dir = os.path.dirname(inspect.getabsfile(entrance[0]))
    modules = _load_all_modules(work_dir, base_dir, regx)

    for mname in modules:
        _logger.info(f"Import controllers from module: {mname}")
        _import_module(mname)


def _prepare_server(host: str = "",
                    port: int = 9090,
                    ssl: bool = False,
                    ssl_protocol: int = PROTOCOL_TLS_SERVER,
                    ssl_check_hostname: bool = False,
                    keyfile: str = "",
                    certfile: str = "",
                    keypass: str = "",
                    ssl_context: SSLContext = None,
                    resources: Dict[str, str] = {},
                    connection_idle_time=None,
                    keep_alive=True,
                    keep_alive_max_request=None,
                    prefer_coroutine=False,
                    app_conf: AppConf = None
                    ) -> None:
    with __lock:
        global _server
        if _server is not None:
            _server.shutdown()
        _server = HttpServer(host=(host, port),
                             ssl=ssl,
                             ssl_protocol=ssl_protocol,
                             ssl_check_hostname=ssl_check_hostname,
                             keyfile=keyfile,
                             certfile=certfile,
                             keypass=keypass,
                             ssl_context=ssl_context,
                             resources=resources,
                             connection_idle_time=connection_idle_time,
                             keep_alive=keep_alive,
                             keep_alive_max_request=keep_alive_max_request,
                             prefer_corountine=prefer_coroutine,
                             app_conf=app_conf)


def start(host: str = "",
          port: int = 9090,
          ssl: bool = False,
          ssl_protocol: int = PROTOCOL_TLS_SERVER,
          ssl_check_hostname: bool = False,
          keyfile: str = "",
          certfile: str = "",
          keypass: str = "",
          ssl_context: SSLContext = None,
          resources: Dict[str, str] = {},
          connection_idle_time=None,
          keep_alive=True,
          keep_alive_max_request=None,
          prefer_coroutine=False,
          app_conf: AppConf = None) -> None:
    _prepare_server(
        host=host,
        port=port,
        ssl=ssl,
        ssl_protocol=ssl_protocol,
        ssl_check_hostname=ssl_check_hostname,
        keyfile=keyfile,
        certfile=certfile,
        keypass=keypass,
        ssl_context=ssl_context,
        resources=resources,
        connection_idle_time=connection_idle_time,
        keep_alive=keep_alive,
        keep_alive_max_request=keep_alive_max_request,
        prefer_coroutine=prefer_coroutine,
        app_conf=app_conf
    )
    # start the server
    _server.start()


async def start_async(host: str = "",
                      port: int = 9090,
                      ssl: bool = False,
                      ssl_protocol: int = PROTOCOL_TLS_SERVER,
                      ssl_check_hostname: bool = False,
                      keyfile: str = "",
                      certfile: str = "",
                      keypass: str = "",
                      ssl_context: SSLContext = None,
                      resources: Dict[str, str] = {},
                      connection_idle_time=None,
                      keep_alive=True,
                      keep_alive_max_request=None,
                      prefer_coroutine=True,
                      app_conf: AppConf = None) -> None:
    _prepare_server(
        host=host,
        port=port,
        ssl=ssl,
        ssl_protocol=ssl_protocol,
        ssl_check_hostname=ssl_check_hostname,
        keyfile=keyfile,
        certfile=certfile,
        keypass=keypass,
        ssl_context=ssl_context,
        resources=resources,
        connection_idle_time=connection_idle_time,
        keep_alive=keep_alive,
        keep_alive_max_request=keep_alive_max_request,
        prefer_coroutine=prefer_coroutine,
        app_conf=app_conf
    )

    # start the server
    await _server.start_async()


def is_ready() -> bool:
    return _server and _server.ready


def stop() -> None:
    with __lock:
        global _server
        if _server is not None:
            _logger.info("Shutting down server...")
            _server.shutdown()
            _server = None
        else:
            _logger.warning("Server is not ready yet.")


def __fill_proxy(proxy: RoutingServer, session_factory: SessionFactory, app_conf: AppConf):
    appconf = app_conf or get_app_conf()
    set_session_factory(session_factory or appconf.session_factory or LocalSessionFactory())
    filters = appconf._get_filters()
    # filter configuration
    for ft in filters:
        proxy.map_filter(ft)

    request_mappings = appconf._get_request_mappings()
    # request mapping
    for ctr in request_mappings:
        proxy.map_controller(ctr)

    ws_handlers = appconf._get_websocket_handlers()

    for hander in ws_handlers:
        proxy.map_websocket_handler(hander)

    err_pages = appconf._get_error_pages()
    for code, func in err_pages.items():
        proxy.map_error_page(code, func)


def init_wsgi_proxy(resources: Dict[str, str] = {}, session_factory: SessionFactory = None, app_conf: AppConf = None) -> WSGIProxy:
    proxy = WSGIProxy(res_conf=resources)
    __fill_proxy(proxy, session_factory, app_conf)
    return proxy


def init_asgi_proxy(resources: Dict[str, str] = {}, session_factory: SessionFactory = None, app_conf: AppConf = None) -> ASGIProxy:
    proxy = ASGIProxy(res_conf=resources)
    __fill_proxy(proxy, session_factory, app_conf)
    return proxy
