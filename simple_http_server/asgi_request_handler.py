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


import html
import io
import simple_http_server.__utils as utils

from typing import Any, Dict, List, Union, Coroutine
from http import HTTPStatus
from .http_request_handler import HTTPRequestHandler
from .logger import get_logger


_logger = get_logger("simple_http_server.asgi_request_server")


class ASGIRequestHandler:

    def __init__(self, routing_conf, scope, receive, send) -> None:
        self.scope: Dict[str, Union[str, bytes]] = scope
        self.receive: Coroutine = receive
        self.send: Coroutine = send

        self.status = 200
        self.__res_headers: Dict[str, List[str]] = {}

        self.routing_conf = routing_conf
        self.headers = self._parse_headers()
        self.query_parameters = utils.decode_query_string(self.query_string)

        # For http only, not for websocket
        self.writer = self
        self.reader = self
        self.req_body: bytearray = bytearray()
        self.req_body_read = False
        self.req_body_reader: io.BytesIO = None

        self.res_body_writer: io.BytesIO = io.BytesIO(b'')

    @property
    def command(self):
        return self.scope['method']

    @property
    def request_path(self):
        path = self.scope['path']
        if path.startswith('/'):
            path = path[1:]
        return path

    @property
    def query_string(self):
        return self.scope['query_string'].decode()

    @property
    def request(self):
        return self

    async def read(self, n: int = -1):
        if self.req_body_read:
            if not self.req_body_reader:
                self.req_body_reader = io.BytesIO(self.req_body)
            return self.req_body_reader.read(n)
        else:
            _logger.warning("Body is not ready yet.")
            return b''

    def write(self, data: bytes):
        self.res_body_writer.write(data)

    def write_eof(self):
        pass

    async def handle_request(self):
        if self.scope["type"] == "websocket":
            self.send_error(501)
            # TODO
            await self.send({"type": "http.response.body"})
        elif self.scope["type"] == "http":
            if "Content-Length" in self.headers:
                while True:
                    recv: dict = await self.receive()
                    if recv["type"] != "http.request":
                        _logger.warn(f"Receive message type[{recv['type']}], return.")
                        return
                    body_chunk = recv.get("body", b'')
                    self.req_body.extend(body_chunk)
                    if not recv.get("more_body", False):
                        self.req_body_read = True
                        break
            handler = HTTPRequestHandler(self, environment=self.scope)
            await handler.handle_request()
            res_start = {
                "type": "http.response.start",
                "status": self.status,
                "headers": []
            }
            for name, val_arr in self.__res_headers.items():
                for val in val_arr:
                    res_start["headers"].append([name.encode(), val.encode()])
            await self.send(res_start)
            await self.send({
                "type": "http.response.body",
                "body": self.res_body_writer.getvalue()
            })

    def send_header(self, name, val):
        name = str(name)
        val = str(val)
        if name not in self.__res_headers:
            self.__res_headers[name] = [val]
        else:
            self.__res_headers[name].append(val)

    def end_headers(self):
        pass

    def _parse_headers(self):
        headers: Dict[str, str] = {}
        for h in self.scope["headers"]:
            name = h[0].decode() if isinstance(h[0], bytes) else str(h[0])
            name = "-".join([p[0].upper() + p[1:].lower() for p in name.split("-")])
            val = h[1].decode() if isinstance(h[1], bytes) else str(h[1])
            headers[name] = val

        return headers

    def send_response(self, code, message=None):
        self.send_response_only(code, message)
        self.send_header('Date', utils.date_time_string())

    def send_response_only(self, code, message=None):
        if message:
            _logger.warning(f"Message[{message}] will be ignore in ASGI mode.")
        self.status = code

    def send_error(self, code: int, message: str = None, explain: str = None, headers: Dict[str, str] = {}):
        """Send and log an error reply.

        Arguments are
        * code:    an HTTP error code
                   3 digits
        * message: a simple optional 1 line reason phrase.
                   *( HTAB / SP / VCHAR / %x80-FF )
                   defaults to short entry matching the response code
        * explain: a detailed message defaults to the long entry
                   matching the response code.

        This sends an error response (so it must be called before any
        output has been generated), logs the error, and finally sends
        a piece of HTML explaining the error to the user.

        """

        try:
            shortmsg, longmsg = self.res_code_msg[code]
        except KeyError:
            shortmsg, longmsg = '???', '???'
        if message is None:
            message = shortmsg
        if explain is None:
            explain = longmsg
        _logger.error(f"code {code}, message {message}")
        self.send_response(code, message)

        # Message body is omitted for cases described in:
        #  - RFC7230: 3.3. 1xx, 204(No Content), 304(Not Modified)
        #  - RFC7231: 6.3.6. 205(Reset Content)
        body = None
        if (code >= 200 and
            code not in (HTTPStatus.NO_CONTENT,
                         HTTPStatus.RESET_CONTENT,
                         HTTPStatus.NOT_MODIFIED)):
            try:
                content: Any = self.routing_conf.error_page(code, html.escape(
                    message, quote=False), html.escape(explain, quote=False))
            except:
                content: str = ""
            content_type, body = utils.decode_response_body_to_bytes(content)

            self.send_header("Content-Type", content_type)
            self.send_header('Content-Length', str(len(body)))
        if headers:
            for h_name, h_val in headers.items():
                self.send_header(h_name, h_val)
        self.end_headers()

        if self.command != 'HEAD' and body:
            self.write(body)
