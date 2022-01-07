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


import json
import socket
import os
import re

import threading
import asyncio

from asyncio.base_events import Server
from concurrent.futures import ThreadPoolExecutor
from asyncio.streams import StreamReader, StreamWriter
from ssl import PROTOCOL_TLS_SERVER, SSLContext
from collections import OrderedDict
from socketserver import TCPServer
from time import sleep
from urllib.parse import unquote

from typing import Any, Callable, Dict, List, Tuple

from simple_http_server import ControllerFunction, StaticFile
from .http_protocol_handler import HttpProtocolHandler, SocketServerStreamRequestHandlerWraper
from .wsgi_request_handler import WSGIRequestHandler

from .__utils import remove_url_first_slash, get_function_args, get_function_kwargs, get_path_reg_pattern
from .logger import get_logger

_logger = get_logger("simple_http_server.http_server")


class RoutingConf:

    HTTP_METHODS = ["OPTIONS", "GET", "HEAD",
                    "POST", "PUT", "DELETE", "TRACE", "CONNECT"]

    def __init__(self, res_conf={}):
        self.method_url_mapping: Dict[str,
                                      Dict[str, ControllerFunction]] = {"_": {}}
        self.path_val_url_mapping: Dict[str, Dict[str, ControllerFunction]] = {
            "_": OrderedDict()}
        self.method_regexp_mapping: Dict[str, Dict[str, ControllerFunction]] = {
            "_": OrderedDict()}
        for mth in self.HTTP_METHODS:
            self.method_url_mapping[mth] = {}
            self.path_val_url_mapping[mth] = OrderedDict()
            self.method_regexp_mapping[mth] = OrderedDict()

        self.filter_mapping = OrderedDict()
        self._res_conf = []
        self.add_res_conf(res_conf)

        self.ws_mapping = OrderedDict()
        self.ws_path_val_mapping = OrderedDict()

        self.error_page_mapping = {}

    @property
    def res_conf(self):
        return self._res_conf

    @res_conf.setter
    def res_conf(self, val: Dict[str, str]):
        self._res_conf.clear()
        self.add_res_conf(val)

    def add_res_conf(self, val: Dict[str, str]):
        if not val or not isinstance(val, dict):
            return
        for res_k, v in val.items():
            if res_k.startswith("/"):
                k = res_k[1:]
            else:
                k = res_k
            if k.endswith("/*"):
                key = k[0:-1]
            elif k.endswith("/**"):
                key = k[0:-2]
            elif k.endswith("/"):
                key = k
            else:
                key = k + "/"

            if v.endswith(os.path.sep):
                val = v
            else:
                val = v + os.path.sep
            self._res_conf.append((key, val))
        self._res_conf.sort(key=lambda it: -len(it[0]))

    def map_controller(self, ctrl: ControllerFunction):
        url = ctrl.url
        regexp = ctrl.regexp
        method = ctrl.method
        _logger.debug(
            f"map url {url}|{regexp} with method[{method}] to function {ctrl.func}. ")
        assert method is None or method == "" or method.upper() in self.HTTP_METHODS
        _method = method.upper() if method is not None and method != "" else "_"
        if regexp:
            self.method_regexp_mapping[_method][regexp] = ctrl
        else:
            _url = remove_url_first_slash(url)

            path_pattern, path_names = get_path_reg_pattern(_url)
            if path_pattern is None:
                self.method_url_mapping[_method][_url] = ctrl
            else:
                self.path_val_url_mapping[_method][path_pattern] = (
                    ctrl, path_names)

    def _res_(self, path, res_pre, res_dir):
        fpath = os.path.join(res_dir, path.replace(res_pre, ""))
        _logger.debug(f"static file. {path} :: {fpath}")
        fext = os.path.splitext(fpath)[1]
        ext = fext.lower()
        if ext in (".html", ".htm", ".xhtml"):
            content_type = "text/html"
        elif ext == ".xml":
            content_type = "text/xml"
        elif ext == ".css":
            content_type = "text/css"
        elif ext in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif ext == ".png":
            content_type = "image/png"
        elif ext == ".webp":
            content_type = "image/webp"
        elif ext == ".js":
            content_type = "text/javascript"
        elif ext == ".pdf":
            content_type = "application/pdf"
        elif ext == ".mp4":
            content_type = "video/mp4"
        elif ext == ".mp3":
            content_type = "audio/mp3"
        else:
            content_type = "application/octet-stream"

        return StaticFile(fpath, content_type)

    def get_url_controller(self, path: str = "", method: str = "") -> Tuple[ControllerFunction, Dict, List]:
        # explicitly url matching
        if path in self.method_url_mapping[method]:
            return self.method_url_mapping[method][path], {}, ()
        elif path in self.method_url_mapping["_"]:
            return self.method_url_mapping["_"][path], {}, ()

        # url with path value matching
        fun_and_val = self.__try_get_from_path_val(path, method)
        if fun_and_val is None:
            fun_and_val = self.__try_get_from_path_val(path, "_")
        if fun_and_val is not None:
            return fun_and_val[0], fun_and_val[1], ()

        # regexp
        func_and_groups = self.__try_get_from_regexp(path, method)
        if func_and_groups is None:
            func_and_groups = self.__try_get_from_regexp(path, "_")
        if func_and_groups is not None:
            return func_and_groups[0], {}, func_and_groups[1]
        # static files
        for k, v in self.res_conf:
            if path.startswith(k):
                def static_fun():
                    return self._res_(path, k, v)
                return ControllerFunction(func=static_fun), {}, ()
        return None, {}, ()

    def __try_get_from_regexp(self, path, method):
        for regex, ctrl in self.method_regexp_mapping[method].items():
            m = re.match(regex, path)
            _logger.debug(
                f"regexp::pattern::[{regex}] => path::[{path}] match? {m is not None}")
            if m:
                return ctrl, tuple([unquote(v) for v in m.groups()])
        return None

    def __try_get_from_path_val(self, path, method):
        for patterns, val in self.path_val_url_mapping[method].items():
            m = re.match(patterns, path)
            _logger.debug(
                f"url with path value::pattern::[{patterns}] => path::[{path}] match? {m is not None}")
            if m:
                fun, path_names = val
                path_values = {}
                for idx in range(len(path_names)):
                    key = unquote(path_names[idx])
                    path_values[key] = unquote(m.groups()[idx])
                return fun, path_values
        return None

    def map_filter(self, filter_conf: Dict[str, Any]):
        # {"path": p, "url_pattern": r, "func": filter_fun}
        path = filter_conf["path"] if "path" in filter_conf else ""
        regexp = filter_conf["url_pattern"]
        filter_fun = filter_conf["func"]
        if path:
            regexp = get_path_reg_pattern(path)[0]
            if not regexp:
                regexp = f"^{path}$"
        _logger.debug(f"[path: {path}] map url regexp {regexp} to function: {filter_fun}")
        self.filter_mapping[regexp] = filter_fun

    def get_matched_filters(self, path):
        return self._get_matched_filters(remove_url_first_slash(path)) + self._get_matched_filters(path)

    def _get_matched_filters(self, path):
        available_filters = []
        for regexp, val in self.filter_mapping.items():
            m = re.match(regexp, path)
            _logger.debug(f"filter:: [{regexp}], path:: [{path}] match? {m is not None}")
            if m:
                available_filters.append(val)
        return available_filters

    def map_websocket_handler(self, endpoint, handler_class):
        url = remove_url_first_slash(endpoint)
        path_pattern, path_names = get_path_reg_pattern(url)
        if path_pattern is None:
            self.ws_mapping[url] = handler_class
        else:
            self.ws_path_val_mapping[path_pattern] = (
                handler_class, path_names)

    def get_websocket_handler(self, path):
        if path in self.ws_mapping:
            return self.ws_mapping[path], {}
        return self.__try_get_ws_handler_from_path_val(path)

    def __try_get_ws_handler_from_path_val(self, path):
        for patterns, val in self.ws_path_val_mapping.items():
            m = re.match(patterns, path)
            _logger.debug(
                f"websocket endpoint with path value::pattern::[{patterns}] => path::[{path}] match? {m is not None}")
            if m:
                clz, path_names = val
                path_values = {}
                for idx in range(len(path_names)):
                    key = unquote(path_names[idx])
                    path_values[key] = unquote(m.groups()[idx])
                return clz, path_values
        return None, {}

    def map_error_page(self, code: str, error_page_fun: Callable):
        if not code:
            c = "_"
        else:
            c = str(code).lower()
        self.error_page_mapping[c] = error_page_fun

    def _default_error_page(self, code: int, message: str = "", explain: str = ""):
        return json.dumps({
            "code": code,
            "message": message,
            "explain": explain
        })

    def error_page(self, code: int, message: str = "", explain: str = ""):
        c = str(code)
        func = None
        if c in self.error_page_mapping:
            func = self.error_page_mapping[c]
        elif code > 200:
            c0x = c[0:2] + "x"
            if c0x in self.error_page_mapping:
                func = self.error_page_mapping[c0x]
            elif "_" in self.error_page_mapping:
                func = self.error_page_mapping["_"]

        if not func:
            func = self._default_error_page
        _logger.debug(f"error page function:: {func}")

        co = code
        msg = message
        exp = explain

        args_def = get_function_args(func, None)
        kwargs_def = get_function_kwargs(func, None)

        args = []
        for n, t in args_def:
            _logger.debug(f"set value to error_page function -> {n}")
            if co is not None:
                if t is None or t == int:
                    args.append(co)
                    co = None
                    continue
            if msg is not None:
                if t is None or t == str:
                    args.append(msg)
                    msg = None
                    continue
            if exp is not None:
                if t is None or t == str:
                    args.append(exp)
                    exp = None
                    continue
            args.append(None)

        kwargs = {}
        for n, v, t in kwargs_def:
            if co is not None:
                if (t is None and isinstance(v, int)) or t == int:
                    kwargs[n] = co
                    co = None
                    continue
            if msg is not None:
                if (t is None and isinstance(v, str)) or t == str:
                    kwargs[n] = msg
                    msg = None
                    continue
            if exp is not None:
                if (t is None and isinstance(v, str)) or t == str:
                    kwargs[n] = exp
                    exp = None
                    continue
            kwargs[n] = v

        if args and kwargs:
            return func(*args, **kwargs)
        elif args:
            return func(*args)
        elif kwargs:
            return func(**kwargs)
        else:
            return func()


class HTTPServer(TCPServer, RoutingConf):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    _default_max_workers = 50

    def server_bind(self):
        """Override server_bind to store the server name."""
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

    def __init__(self, addr, res_conf={}, max_workers: int = None):
        TCPServer.__init__(self, addr, SocketServerStreamRequestHandlerWraper)
        RoutingConf.__init__(self, res_conf)
        self.max_workers = max_workers or self._default_max_workers
        self.threadpool: ThreadPoolExecutor = ThreadPoolExecutor(
            thread_name_prefix="ReqThread",
            max_workers=self.max_workers)

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    # override
    def process_request(self, request, client_address):
        self.threadpool.submit(self.process_request_thread, request, client_address)

    def server_close(self):
        super().server_close()
        self.threadpool.shutdown(True)

    def start(self):
        self.serve_forever()

    def _shutdown(self) -> None:
        _logger.debug("shutdown http server in a seperate thread..")
        super().shutdown()

    def shutdown(self) -> None:
        threading.Thread(target=self._shutdown, daemon=False).start()


class CoroutineHTTPServer(RoutingConf):

    def __init__(self, host: str = '', port: int = 9090, ssl: SSLContext = None, res_conf={}) -> None:
        RoutingConf.__init__(self, res_conf)
        self.host: str = host
        self.port: int = port
        self.ssl: SSLContext = ssl
        self.server: Server = None

    async def callback(self, reader: StreamReader, writer: StreamWriter):
        handler = HttpProtocolHandler(reader, writer, routing_conf=self)
        await handler.handle_request()
        _logger.debug("Connection ends, close the writer.")
        writer.close()

    async def start_server(self):
        self.server = await asyncio.start_server(
            self.callback, host=self.host, port=self.port, ssl=self.ssl)
        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.exceptions.CancelledError:
                _logger.debug(
                    "Some requests are lost for the reason that the server is shutted down.")
            finally:
                await self.server.wait_closed()

    def start(self):
        asyncio.run(self.start_server())

    def _shutdown(self):
        _logger.debug("Try to shutdown server.")
        self.server.close()
        loop = self.server.get_loop()
        loop.call_soon_threadsafe(loop.stop)

    def shutdown(self):
        wait_time = 3
        while wait_time:
            sleep(1)
            _logger.debug(f"couting to shutdown: {wait_time}")
            wait_time = wait_time - 1
            if wait_time == 0:
                _logger.debug("shutdown server....")
                self._shutdown()


class SimpleDispatcherHttpServer:
    """Dispatcher Http server"""

    def map_filter(self, filter_conf):
        self.server.map_filter(filter_conf)

    def map_controller(self, ctrl: ControllerFunction):
        self.server.map_controller(ctrl)

    def map_websocket_handler(self, endpoint, handler_class):
        self.server.map_websocket_handler(endpoint, handler_class)

    def map_error_page(self, code, func):
        self.server.map_error_page(code, func)

    def __init__(self,
                 host: Tuple[str, int] = ('', 9090),
                 ssl: bool = False,
                 ssl_protocol: int = PROTOCOL_TLS_SERVER,
                 ssl_check_hostname: bool = False,
                 keyfile: str = "",
                 certfile: str = "",
                 keypass: str = "",
                 ssl_context: SSLContext = None,
                 resources: Dict[str, str] = {},
                 prefer_corountine=False,
                 max_workers: int = None):
        self.host = host
        self.__ready = False

        self.ssl = ssl

        if ssl:
            if ssl_context:
                self.ssl_ctx = ssl_context
            else:
                assert keyfile and certfile, "keyfile and certfile should be provided. "
                ssl_ctx = SSLContext(protocol=ssl_protocol)
                ssl_ctx.check_hostname = ssl_check_hostname
                ssl_ctx.load_cert_chain(
                    certfile=certfile, keyfile=keyfile, password=keypass)
                self.ssl_ctx = ssl_ctx
        else:
            self.ssl_ctx = None

        if prefer_corountine:
            _logger.info(f"Start server in corouting mode, listen to port: {self.host[1]}")
            self.server = CoroutineHTTPServer(
                self.host[0], self.host[1], self.ssl_ctx, resources)
        else:
            _logger.info(f"Start server in threading mixed mode, listen to port {self.host[1]}")
            self.server = HTTPServer(self.host, resources, max_workers=max_workers)
            if self.ssl_ctx:
                self.server.socket = self.ssl_ctx.wrap_socket(
                    self.server.socket, server_side=True)

    @property
    def ready(self):
        return self.__ready

    def resources(self, res={}):
        self.server.res_conf = res

    def start(self):
        try:
            self.__ready = True
            self.server.start()
        except:
            self.__ready = False
            raise

    def shutdown(self):
        # shutdown it in a seperate thread.
        self.server.shutdown()


class WSGIProxy(RoutingConf):

    def __init__(self, res_conf):
        super().__init__(res_conf=res_conf)

    def app_proxy(self, environment, start_response):
        return asyncio.run(self.async_app_proxy(environment, start_response))

    async def async_app_proxy(self, environment, start_response):
        requestHandler = WSGIRequestHandler(self, environment, start_response)
        return await requestHandler.handle_request()
