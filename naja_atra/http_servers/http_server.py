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


import asyncio

from ssl import PROTOCOL_TLS_SERVER, SSLContext

from typing import Dict,  Tuple
from .coroutine_http_server import CoroutineHTTPServer
from .threading_http_server import ThreadingHTTPServer

from ..models.model_bindings import ModelBindingConf

from ..app_conf import ControllerFunction, WebsocketHandlerClass, AppConf, get_app_conf, _get_session_factory
from .routing_server import RoutingServer
from ..request_handlers.wsgi_request_handler import WSGIRequestHandler
from ..request_handlers.asgi_request_handler import ASGIRequestHandler

from ..utils.logger import get_logger


_logger = get_logger("simple_http.http_server")


class HttpServer:
    """Dispatcher Http server"""

    def map_filter(self, filter_conf):
        self.server.map_filter(filter_conf)

    def map_controller(self, ctrl: ControllerFunction):
        self.server.map_controller(ctrl)

    def map_websocket_handler(self, handler: WebsocketHandlerClass):
        self.server.map_websocket_handler(handler)

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
                 max_workers: int = None,
                 connection_idle_time=None,
                 keep_alive=True,
                 keep_alive_max_request=None,
                 gzip_content_types=set(),
                 gzip_compress_level=9,
                 app_conf: AppConf = None):
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

        appconf = app_conf or get_app_conf()
        if prefer_corountine:
            _logger.info(
                f"Start server in corouting mode, listen to port: {self.host[1]}")
            self.server = CoroutineHTTPServer(
                self.host[0], self.host[1], self.ssl_ctx, resources, model_binding_conf=appconf.model_binding_conf)
        else:
            _logger.info(
                f"Start server in threading mixed mode, listen to port {self.host[1]}")
            self.server = ThreadingHTTPServer(
                self.host, resources, model_binding_conf=appconf.model_binding_conf, max_workers=max_workers)
            if self.ssl_ctx:
                self.server.socket = self.ssl_ctx.wrap_socket(
                    self.server.socket, server_side=True)

        self.server.gzip_compress_level = gzip_compress_level
        self.server.gzip_content_types = gzip_content_types

        filters = appconf._get_filters()
        # filter configuration
        for ft in filters:
            self.map_filter(ft)

        request_mappings = appconf._get_request_mappings()
        # request mapping
        for ctr in request_mappings:
            self.map_controller(ctr)

        ws_handlers = appconf._get_websocket_handlers()

        for wshandler in ws_handlers:
            self.map_websocket_handler(wshandler)

        err_pages = appconf._get_error_pages()
        for code, func in err_pages.items():
            self.map_error_page(code, func)
        self.server.keep_alive = keep_alive
        self.server.connection_idle_time = connection_idle_time
        self.server.keep_alive_max_request = keep_alive_max_request
        self.server.session_factory = appconf.session_factory or _get_session_factory()

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

    async def start_async(self):
        try:
            self.__ready = True
            await self.server.start_async()
        except:
            self.__ready = False
            raise

    def shutdown(self):
        # shutdown it in a seperate thread.
        self.server.shutdown()


class WSGIProxy(RoutingServer):

    def __init__(self, res_conf, model_binding_conf: ModelBindingConf = ModelBindingConf()):
        super().__init__(res_conf=res_conf, model_binding_conf=model_binding_conf)

    def app_proxy(self, environment, start_response):
        return asyncio.run(self.async_app_proxy(environment, start_response))

    async def async_app_proxy(self, environment, start_response):
        request_handler = WSGIRequestHandler(self, environment, start_response)
        return await request_handler.handle_request()


class ASGIProxy(RoutingServer):

    def __init__(self, res_conf, model_binding_conf: ModelBindingConf = ModelBindingConf()):
        super().__init__(res_conf=res_conf, model_binding_conf=model_binding_conf)

    async def app_proxy(self, scope, receive, send):
        request_handler = ASGIRequestHandler(self, scope, receive, send)
        await request_handler.handle_request()
