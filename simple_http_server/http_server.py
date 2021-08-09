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
import ssl as _ssl
import threading
import time
import asyncio

from collections import OrderedDict
from socketserver import ThreadingMixIn, TCPServer
from types import coroutine
from urllib.parse import unquote
from urllib.parse import quote

from typing import Callable, Dict, List, Tuple

from simple_http_server import ControllerFunction, StaticFile

from .base_request_handler import BaseHTTPRequestHandler
from .wsgi_request_handler import WSGIRequestHandler
from .__utils import remove_url_first_slash, get_function_args, get_function_kwargs
from .logger import get_logger

_logger = get_logger("simple_http_server.http_server")


class RoutingConf:

    HTTP_METHODS = ["OPTIONS", "GET", "HEAD", "POST", "PUT", "DELETE", "TRACE", "CONNECT"]

    def __init__(self, res_conf={}):
        self.method_url_mapping: Dict[str, Dict[str, ControllerFunction]] = {"_": {}}
        self.path_val_url_mapping: Dict[str, Dict[str, ControllerFunction]] = {"_": OrderedDict()}
        self.method_regexp_mapping: Dict[str, Dict[str, ControllerFunction]] = {"_": OrderedDict()}
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

    def __get_path_reg_pattern(self, url):
        _url: str = url
        path_names = re.findall("(?u)\\{\\w+\\}", _url)
        if len(path_names) == 0:
            # normal url
            return None, path_names
        for name in path_names:
            _url = _url.replace(name, "([\\w%.-@!\\(\\)\\[\\]\\|\\$]+)")
        _url = f"^{_url}$"

        quoted_names = []
        for name in path_names:
            name = name[1: -1]
            quoted_names.append(quote(name))
        return _url, quoted_names

    def map_controller(self, ctrl: ControllerFunction):
        url = ctrl.url
        regexp = ctrl.regexp
        method = ctrl.method
        _logger.debug(f"map url {url}|{regexp} with method[{method}] to function {ctrl.func}. ")
        assert method is None or method == "" or method.upper() in self.HTTP_METHODS
        _method = method.upper() if method is not None and method != "" else "_"
        if regexp:
            self.method_regexp_mapping[_method][regexp] = ctrl
        else:
            _url = remove_url_first_slash(url)

            path_pattern, path_names = self.__get_path_reg_pattern(_url)
            if path_pattern is None:
                self.method_url_mapping[_method][_url] = ctrl
            else:
                self.path_val_url_mapping[_method][path_pattern] = (ctrl, path_names)

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

    def get_url_controller(self, path="", method="") -> Tuple[ControllerFunction, Dict, List]:
        decoded_path = unquote(path)
        # explicitly url matching
        if decoded_path in self.method_url_mapping[method]:
            return self.method_url_mapping[method][decoded_path], {}, ()
        elif decoded_path in self.method_url_mapping["_"]:
            return self.method_url_mapping["_"][decoded_path], {}, ()

        # url with path value matching
        fun_and_val = self.__try_get_from_path_val(decoded_path, method)
        if fun_and_val is None:
            fun_and_val = self.__try_get_from_path_val(decoded_path, "_")
        if fun_and_val is not None:
            return fun_and_val[0], fun_and_val[1], ()

        # regexp
        func_and_groups = self.__try_get_from_regexp(decoded_path, method)
        if func_and_groups is None:
            func_and_groups = self.__try_get_from_regexp(decoded_path, "_")
        if func_and_groups is not None:
            return func_and_groups[0], {}, func_and_groups[1]
        # static files
        for k, v in self.res_conf:
            if decoded_path.startswith(k):
                def static_fun():
                    return self._res_(decoded_path, k, v)
                return ControllerFunction(func=static_fun), {}, ()
        return None, {}, ()

    def __try_get_from_regexp(self, path, method):
        for regex, ctrl in self.method_regexp_mapping[method].items():
            m = re.match(regex, path)
            _logger.debug(f"regexp::pattern::[{regex}] => path::[{path}] match? {m is not None}")
            if m:
                return ctrl, tuple([unquote(v) for v in m.groups()])
        return None

    def __try_get_from_path_val(self, path, method):
        for patterns, val in self.path_val_url_mapping[method].items():
            m = re.match(patterns, path)
            _logger.debug(f"url with path value::pattern::[{patterns}] => path::[{path}] match? {m is not None}")
            if m:
                fun, path_names = val
                path_values = {}
                for idx in range(len(path_names)):
                    key = unquote(path_names[idx])
                    path_values[key] = unquote(m.groups()[idx])
                return fun, path_values
        return None

    def map_filter(self, path_pattern, filter_fun):
        self.filter_mapping[path_pattern] = filter_fun

    def get_matched_filters(self, path):
        available_filters = []
        for key, val in self.filter_mapping.items():
            if re.match(key, path):
                available_filters.append(val)
        return available_filters

    def map_websocket_handler(self, endpoint, handler_class):
        url = remove_url_first_slash(endpoint)
        path_pattern, path_names = self.__get_path_reg_pattern(url)
        if path_pattern is None:
            self.ws_mapping[url] = handler_class
        else:
            self.ws_path_val_mapping[path_pattern] = (handler_class, path_names)

    def get_websocket_handler(self, path):
        if path in self.ws_mapping:
            return self.ws_mapping[path], {}
        return self.__try_get_ws_handler_from_path_val(path)

    def __try_get_ws_handler_from_path_val(self, path):
        for patterns, val in self.ws_path_val_mapping.items():
            m = re.match(patterns, path)
            _logger.debug(f"websocket endpoint with path value::pattern::[{patterns}] => path::[{path}] match? {m is not None}")
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

    def server_bind(self):
        """Override server_bind to store the server name."""
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

    def __init__(self, addr, res_conf={}):
        TCPServer.__init__(self, addr, BaseHTTPRequestHandler)
        RoutingConf.__init__(self, res_conf)


class ThreadingMixInHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class AsyncioMixin:

    DEFAULT_QUEUE_SIZE = 100

    def __init__(self) -> None:
        # All the coroutine tasks will run in this thread.
        self.__coroutine_thread: threading.Thread = threading.Thread(target=self.coroutine_main, name="coroutine-thread", daemon=True)
        self.__coroutine_thread.start()
        self.__loop = None
        self.__coroutine_tasks = {}

    def put_coroutine_task(self, request, task):
        if request in self.__coroutine_tasks:
            self.__coroutine_tasks[request].append(task)
        else:
            self.__coroutine_tasks[request] = [task]

    def coroutine_main(self):
        self.__loop = loop = asyncio.new_event_loop()
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            _logger.info("End of the coroutine....")

    async def process_request_async(self, request, client_address):
        """Same as in BaseServer but as async.

        In addition, exception handling is done here.

        """
        _logger.debug("do request in a coroutine task!")
        try:
            self.finish_request(request, client_address)
            if request in self.__coroutine_tasks:
                coroutine_tasks = self.__coroutine_tasks[request]
                _logger.debug(f"{len(coroutine_tasks)} corotine task(s) are(is) found assoiated with this request, await them(it)")
                for task in coroutine_tasks:
                    await task
                del self.__coroutine_tasks[request]
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        asyncio.run_coroutine_threadsafe(self.process_request_async(request, client_address), self.__loop)

    def server_close(self):
        super().server_close()
        self.__loop.stop()
        self.__coroutine_thread.join()

    def shutdown(self):
        super().shutdown()
        self.__loop.stop()
        self.__coroutine_thread.join()
        _logger.debug("shutdown....join thread...")


class AsyncioMixInHTTPServer(AsyncioMixin, HTTPServer):

    def __init__(self, addr, res_conf={}):
        HTTPServer.__init__(self, addr, res_conf=res_conf)
        AsyncioMixin.__init__(self)


class SimpleDispatcherHttpServer:
    """Dispatcher Http server"""

    def map_filter(self, path_pattern, filter_fun):
        self.server.map_filter(path_pattern, filter_fun)

    def map_controller(self, ctrl: ControllerFunction):
        self.server.map_controller(ctrl)

    def map_websocket_handler(self, endpoint, handler_class):
        self.server.map_websocket_handler(endpoint, handler_class)

    def map_error_page(self, code, func):
        self.server.map_error_page(code, func)

    def __init__(self,
                 host: Tuple[str, int] = ('', 9090),
                 ssl: bool = False,
                 ssl_protocol: int = _ssl.PROTOCOL_TLS_SERVER,
                 ssl_check_hostname: bool = False,
                 keyfile: str = "",
                 certfile: str = "",
                 keypass: str = "",
                 ssl_context: _ssl.SSLContext = None,
                 resources: Dict[str, str] = {},
                 prefer_corountine=False):
        self.host = host
        self.__ready = False

        self.ssl = ssl
        if prefer_corountine:
            self.server = AsyncioMixInHTTPServer(self.host, res_conf=resources)
        else:
            self.server = ThreadingMixInHTTPServer(self.host, res_conf=resources)

        if ssl:
            if ssl_context:
                ssl_ctx = ssl_context
            else:
                assert keyfile and certfile, "keyfile and certfile should be provided. "
                ssl_ctx = _ssl.SSLContext(protocol=ssl_protocol)
                ssl_ctx.check_hostname = ssl_check_hostname
                ssl_ctx.load_cert_chain(certfile=certfile, keyfile=keyfile, password=keypass)
            self.server.socket = ssl_ctx.wrap_socket(
                self.server.socket,
                server_side=True
            )

    @property
    def ready(self):
        return self.__ready

    def resources(self, res={}):
        self.server.res_conf = res

    def start(self):
        if self.ssl:
            ssl_hint = " with SSL on"
        else:
            ssl_hint = ""
        _logger.info(f"Dispatcher Http Server starts. Listen to port [{self.host[1]}]{ssl_hint}.")
        try:
            self.__ready = True
            self.server.serve_forever()
        except:
            self.__ready = False
            raise

    def shutdown(self):
        def shut():
            for i in (3, 2, 1, 0):
                _logger.info(f"server receives a shutdown signal, will shut the server in {i} second(s). ")
                time.sleep(1)
            self.server.shutdown()
        threading.Thread(target=shut, daemon=True).start()


class WSGIProxy(RoutingConf):

    def __init__(self, res_conf):
        super().__init__(res_conf=res_conf)

    def app_proxy(self, environment, start_response):
        requestHandler = WSGIRequestHandler(self, environment, start_response)
        return requestHandler.handle()
