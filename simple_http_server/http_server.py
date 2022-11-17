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


import socket

import threading
import asyncio

from asyncio.base_events import Server
from concurrent.futures import ThreadPoolExecutor
from asyncio.streams import StreamReader, StreamWriter
from ssl import PROTOCOL_TLS_SERVER, SSLContext
from socketserver import TCPServer
from time import sleep

from typing import Dict,  Tuple

from simple_http_server import ControllerFunction, WebsocketHandlerClass
from .http_protocol_handler import HttpProtocolHandler, SocketServerStreamRequestHandlerWraper
from .wsgi_request_handler import WSGIRequestHandler


from .logger import get_logger
from .routing_server import RoutingServer

_logger = get_logger("simple_http_server.http_server")


class HTTPServer(TCPServer, RoutingServer):

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
        RoutingServer.__init__(self, res_conf)
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
        self.threadpool.submit(
            self.process_request_thread, request, client_address)

    def server_close(self):
        super().server_close()
        self.threadpool.shutdown(True)

    def start(self):
        self.serve_forever()

    async def start_async(self):
        self.start()

    def _shutdown(self) -> None:
        _logger.debug("shutdown http server in a seperate thread..")
        super().shutdown()

    def shutdown(self) -> None:
        threading.Thread(target=self._shutdown, daemon=False).start()


class CoroutineHTTPServer(RoutingServer):

    def __init__(self, host: str = '', port: int = 9090, ssl: SSLContext = None, res_conf={}) -> None:
        RoutingServer.__init__(self, res_conf)
        self.host: str = host
        self.port: int = port
        self.ssl: SSLContext = ssl
        self.server: Server = None
        self.__thread_local = threading.local()

    async def callback(self, reader: StreamReader, writer: StreamWriter):
        handler = HttpProtocolHandler(reader, writer, routing_conf=self)
        await handler.handle_request()
        _logger.debug("Connection ends, close the writer.")
        writer.close()

    async def start_async(self):
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

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        if not hasattr(self.__thread_local, "event_loop"):
            try:
                self.__thread_local.event_loop = asyncio.new_event_loop()
            except:
                self.__thread_local.event_loop = asyncio.get_event_loop()
        return self.__thread_local.event_loop

    def start(self):
        self._get_event_loop().run_until_complete(self.start_async())

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
            _logger.info(
                f"Start server in corouting mode, listen to port: {self.host[1]}")
            self.server = CoroutineHTTPServer(
                self.host[0], self.host[1], self.ssl_ctx, resources)
        else:
            _logger.info(
                f"Start server in threading mixed mode, listen to port {self.host[1]}")
            self.server = HTTPServer(
                self.host, resources, max_workers=max_workers)
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

    def __init__(self, res_conf):
        super().__init__(res_conf=res_conf)

    def app_proxy(self, environment, start_response):
        return asyncio.run(self.async_app_proxy(environment, start_response))

    async def async_app_proxy(self, environment, start_response):
        request_handler = WSGIRequestHandler(self, environment, start_response)
        return await request_handler.handle_request()
