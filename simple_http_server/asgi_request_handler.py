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

from typing import Any, Dict, List, Tuple, Union, Coroutine
from http import HTTPStatus
from .http_request_handler import HTTPRequestHandler
from .logger import get_logger
from .websocket_request_handler import *

_logger = get_logger("simple_http_server.asgi_request_server")


class ASGIRequestHandler:

    res_code_msg = {
        v: (v.phrase, v.description)
        for v in HTTPStatus.__members__.values()
    }

    def __init__(self, routing_conf, scope, receive, send) -> None:
        self.scope: Dict[str, Union[str, bytes]] = scope
        self.receive: Coroutine = receive
        self.send: Coroutine = send

        self.status = 200
        self._res_headers: Dict[str, List[str]] = {}

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
        self.request_writer = None

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
        if self.scope["type"] == "http":
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

            res_headers: List[List] = []
            for name, val_arr in self._res_headers.items():
                for val in val_arr:
                    res_headers.append([name.encode(), val.encode()])

            await self.send({
                "type": "http.response.start",
                "status": self.status,
                "headers": res_headers
            })
            await self.send({
                "type": "http.response.body",
                "body": self.res_body_writer.getvalue()
            })
        elif self.scope["type"] == "websocket":
            handler = ASGIWebsocketRequestHandler(self)
            await handler.handle_request()
        else:
            _logger.error(f"Do nost support scope type:: {self.scope['type']}")

    def send_header(self, name, val):
        name = str(name)
        val = str(val)
        if name not in self._res_headers:
            self._res_headers[name] = [val]
        else:
            self._res_headers[name].append(val)

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


class ASGIWebsocketRequestHandler(WebsocketRequestHandler):

    def __init__(self, http_protocol_handler: ASGIRequestHandler) -> None:
        super().__init__(http_protocol_handler)
        self.http_protocol_handler = http_protocol_handler

        self.out_msg_queue: asyncio.Queue = asyncio.Queue()

    @property
    def response_headers(self) -> Dict[str, List[str]]:
        return ""

    async def handle_request(self):
        await self.handshake()
        if not self.keep_alive:
            return

        await asyncio.gather(
            self._receive(),
            self._send())

        await self.on_close()

    async def handshake(self):
        subprotocol: str = None
        headers: List[List[str]] = []
        if self.handler:
            code, hs = await self.on_handshake()
            if code and code != 101:
                self.keep_alive = False
                self.send_response(code)
            else:
                self.send_response(101)
            if hs:
                for h_name, h_val in hs.items():
                    if h_name.lower() == "sec-websocket-protocol":
                        subprotocol = str(h_val)
                        continue
                    name = h_name.encode()
                    if isinstance(h_val, bytes):
                        headers.append[name, h_val]
                    elif isinstance(h_val, list):
                        for val in h_val:
                            headers.append[name, str(val).encode()]
                    else:
                        headers.append([name, str(h_val).encode()])

        else:
            self.keep_alive = False
            self.send_response(404)

        if self.keep_alive:
            await self.http_protocol_handler.send({
                "type": "websocket.accept",
                "subprotocol": subprotocol,
                "headers": headers
            })
            await self.on_open()
        else:
            await self.http_protocol_handler.send({
                "type": "websocket.close",
                "code": self.http_protocol_handler.status,
                "reason": "Handshake error!"
            })

    async def _receive(self):
        while self.keep_alive:
            msg: dict = await self.http_protocol_handler.receive()
            if msg["type"] == "websocket.connect":
                _logger.debug(f"Websocket is connected.")
            elif msg["type"] == "websocket.disconnect":
                self.keep_alive = False
                self.close_reason = WebsocketCloseReason("Client asked to close connection.", code=msg.get("code", 1005), reason='')
                self.out_msg_queue.put_nowait({
                    "type": "websocket.close.client"
                })
            elif msg["type"] == "websocket.receive":
                try:
                    if "text" in msg and msg["text"] is not None and hasattr(self.handler, "on_text_message") and callable(self.handler.on_text_message):
                        await self.await_func(self.handler.on_text_message(self.session, msg["text"]))
                    elif "bytes" in msg and msg["bytes"] is not None and hasattr(self.handler, "on_binary_message") and callable(self.handler.on_binary_message):
                        await self.await_func(self.handler.on_binary_message(self.session, msg["bytes"]))
                    else:
                        _logger.error(f"Cannot read message from ASGI receive event")
                except Exception as e:
                    _logger.error(f"Error occurs when on message!", exc_info=True)
                    self.close(f"Error occurs when on_message. {e}")
            else:
                _logger.error(f"Cannot handle message type {msg['type']}")

    async def _send(self):
        while self.keep_alive:
            msg = await self.out_msg_queue.get()
            if msg["type"] != "websocket.close.client":
                await self.http_protocol_handler.send(msg)

    def calculate_response_key(self):
        return NotImplemented

    async def read_bytes(self, num):
        return NotImplemented

    async def _read_message_content(self) -> Tuple[int, int, bytearray]:
        return NotImplemented

    async def read_next_message(self):
        return NotImplemented

    def send_ping(self, message: Union[str, bytes]):
        raise WebsocketException(WebsocketCloseReason(reason="ASGI cannot send ping message."))

    def send_pong(self, message: Union[str, bytes]):
        raise WebsocketException(WebsocketCloseReason(reason="ASGI cannot send pong message."))

    def _send_bytes_no_lock(self, opcode: int, payload: bytes, chunk_size: int = 0):
        return NotImplemented

    def _send_frame(self, fin: int, opcode: int, payload: bytes):
        return NotImplemented

    def _create_frame_header(self, fin: int, opcode: int, payload_length: int) -> bytes:
        return NotImplemented

    def send_file(self, path: str, chunk_size: int = 0):
        raise WebsocketException(WebsocketCloseReason(reason="ASGI cannot send file message."))

    def _send_file_no_lock(self, path: str, file_size: int, chunk_size: int):
        return NotImplemented

    def send_bytes(self, opcode: int, payload: bytes, chunk_size: int = 0):
        if opcode == WEBSOCKET_OPCODE_TEXT:
            self.send_message(payload.decode(DEFAULT_ENCODING), chunk_size=chunk_size)
        elif opcode == WEBSOCKET_OPCODE_BINARY:
            self.send_message(payload, chunk_size=chunk_size)
        else:
            _logger.error(f"Cannot send websocket with opcode [{opcode}]")

    def send_message(self, message: Union[str, bytes], chunk_size: int = 0):
        if chunk_size != 0:
            _logger.warning(f"chunk_size is not supported in ASGI mode, ignore it.")
        if isinstance(message, bytes):
            self.out_msg_queue.put_nowait({
                "type": "websocket.send",
                "bytes": message
            })
        elif isinstance(message, str):
            self.out_msg_queue.put_nowait({
                "type": "websocket.send",
                "text": message
            })
        else:
            _logger.error(f"Cannot send message[{message}. ")

    def close(self, reason: str = ""):
        self.keep_alive = False
        self.close_reason = WebsocketCloseReason("Server asked to close connection.")
        self.out_msg_queue.put_nowait({
            "type": "websocket.close",
            "reason": reason
        })
