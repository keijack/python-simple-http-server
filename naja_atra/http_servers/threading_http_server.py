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


from .routing_server import RoutingServer
from ..request_handlers.model_bindings import ModelBindingConf
from ..request_handlers.http_request_handler import SocketServerStreamRequestHandlerWraper


import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from socketserver import TCPServer

from ..utils.logger import get_logger


_logger = get_logger("naja_atra.http_servers.threading_http_server")


class ThreadingHTTPServer(TCPServer, RoutingServer):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    _default_max_workers = 50

    def server_bind(self):
        """Override server_bind to store the server name."""
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

    def __init__(self, addr, res_conf={},  model_binding_conf: ModelBindingConf = ModelBindingConf(), max_workers: int = None):
        RoutingServer.__init__(
            self, res_conf, model_binding_conf=model_binding_conf)
        self.max_workers = max_workers or self._default_max_workers
        self.threadpool: ThreadPoolExecutor = ThreadPoolExecutor(
            thread_name_prefix="ReqThread",
            max_workers=self.max_workers)
        TCPServer.__init__(self, addr, SocketServerStreamRequestHandlerWraper)

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
