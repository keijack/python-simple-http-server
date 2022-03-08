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

import struct
from base64 import b64encode
from hashlib import sha1
from typing import Dict, Tuple, Union
from uuid import uuid4
from socket import error as SocketError
import errno


from .logger import get_logger
from simple_http_server import Headers, WebsocketRequest, WebsocketSession

_logger = get_logger("simple_http_server.websocket_request_handler")


'''
https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers

+-+-+-+-+-------+-+-------------+-------------------------------+
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
'''

FIN = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE_CONN = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

OPTYPES = {
    OPCODE_TEXT: "TEXT",
    OPCODE_PING: "PING",
    OPCODE_PONG: "PONE",
    OPCODE_BINARY: "BINARY"
}


class _ContinuationMessageCache:

    def __init__(self, opcode: int) -> None:
        self.opcode: int = opcode
        self.message_bytes: bytearray = bytearray()


class WebsocketRequestHandler:

    GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

    def __init__(self, http_protocol_handler) -> None:
        self.base_http_quest_handler = http_protocol_handler
        self.request_writer = http_protocol_handler.request_writer
        self.routing_conf = http_protocol_handler.routing_conf
        self.send_response = http_protocol_handler.send_response_only
        self.send_header = http_protocol_handler.send_header
        self.reader = http_protocol_handler.reader
        self.keep_alive = True
        self.handshake_done = False

        handler_class, path_values = self.routing_conf.get_websocket_handler(
            http_protocol_handler.request_path)
        self.handler = handler_class() if handler_class else None
        self.ws_request = WebsocketRequest()
        self.ws_request.headers = http_protocol_handler.headers
        self.ws_request.path = http_protocol_handler.request_path
        self.ws_request.query_string = http_protocol_handler.query_string
        self.ws_request.parameters = http_protocol_handler.query_parameters
        self.ws_request.path_values = path_values
        if "cookie" in self.ws_request.headers:
            self.ws_request.cookies.load(self.ws_request.headers["cookie"])
        elif "Cookie" in self.ws_request.headers:
            self.ws_request.cookies.load(self.ws_request.headers["Cookie"])
        self.session = WebsocketSessionImpl(self, self.ws_request)
        self.close_reason: str = ""

        self._continution_cache: _ContinuationMessageCache = None

    @property
    def response_headers(self):
        if hasattr(self.base_http_quest_handler, "_headers_buffer"):
            return self.base_http_quest_handler._headers_buffer
        else:
            return []

    async def await_func(self, obj):
        if asyncio.iscoroutine(obj):
            return await obj
        return obj

    async def on_handshake(self) -> Tuple[int, Dict[str, str]]:
        if not hasattr(self.handler, "on_handshake") or not callable(self.handler.on_handshake):
            return None, {}
        res = await self.await_func(self.handler.on_handshake(self.ws_request))
        http_status_code = None
        headers = {}
        if not res:
            pass
        elif isinstance(res, int):
            http_status_code = res
        elif isinstance(res, dict) or isinstance(res, Headers):
            headers = res
        elif isinstance(res, tuple):
            for item in res:
                if isinstance(item, int) and not http_status_code:
                    http_status_code = item
                elif isinstance(item, dict) or isinstance(item, Headers):
                    headers.update(item)
        else:
            _logger.warn(f"Endpoint[{self.ws_request.path}]")
        return http_status_code, headers

    async def on_message(self, opcode: int, message_bytes: bytes):
        if opcode == OPCODE_TEXT and hasattr(self.handler, "on_text_message") and callable(self.handler.on_text_message):
            await self.await_func(self.handler.on_text_message(self.session, self._try_decode_UTF8(message_bytes)))
        elif opcode == OPCODE_PING and hasattr(self.handler, "on_ping_message") and callable(self.handler.on_ping_message):
            await self.await_func(self.handler.on_ping_message(self.session, bytes(message_bytes)))
        elif opcode == OPCODE_PONG and hasattr(self.handler, "on_pong_message") and callable(self.handler.on_pong_message):
            await self.await_func(self.handler.on_pong_message(self.session, bytes(message_bytes)))
        elif opcode == OPCODE_BINARY and hasattr(self.handler, "on_binary_message") and callable(self.handler.on_binary_message):
            await self.await_func(self.handler.on_binary_message(self.session, bytes(message_bytes)))

    async def on_continuation_frame(self, opcode: int, fin: bool, message_frame: bytearray):
        if opcode != OPCODE_BINARY:
            self._continution_cache.message_bytes.extend(message_frame)
            return

        if hasattr(self.handler, "on_binary_frame") and callable(self.handler.on_binary_frame):
            should_append_to_cache = await self.await_func(self.handler.on_binary_frame(self.session, fin, bytes(message_frame)))
            _logger.debug(f"Should append to binary Cache? {should_append_to_cache}")
            if should_append_to_cache == True:
                self._continution_cache.message_bytes.extend(message_frame)
        else:
            self._continution_cache.message_bytes.extend(message_frame)

    async def on_open(self):
        if hasattr(self.handler, "on_open") and callable(self.handler.on_open):
            await self.await_func(self.handler.on_open(self.session))

    async def on_close(self):
        if hasattr(self.handler, "on_close") and callable(self.handler.on_close):
            await self.await_func(self.handler.on_close(self.session, self.close_reason))

    async def handle_request(self):
        while self.keep_alive:
            if not self.handshake_done:
                await self.handshake()
            else:
                await self.read_next_message()

        await self.on_close()

    async def handshake(self):
        if self.handler:
            code, headers = await self.on_handshake()
            if code and code != 101:
                self.keep_alive = False
                self.send_response(code)
            else:
                self.send_response(101, "Switching Protocols")
                self.send_header("Upgrade", "websocket")
                self.send_header("Connection", "Upgrade")
                self.send_header("Sec-WebSocket-Accept",
                                 self.calculate_response_key())
            if headers:
                for h_name, h_val in headers.items():
                    self.send_header(h_name, h_val)
        else:
            self.keep_alive = False
            self.send_response(404)

        ws_res_headers = b"".join(self.response_headers) + b"\r\n"
        _logger.debug(ws_res_headers)
        self.request_writer.send(ws_res_headers)
        self.handshake_done = True
        if self.keep_alive == True:
            await self.on_open()

    def calculate_response_key(self):
        _logger.debug(
            f"Sec-WebSocket-Key: {self.ws_request.headers['Sec-WebSocket-Key']}")
        key: str = self.ws_request.headers["Sec-WebSocket-Key"]
        hash = sha1(key.encode() + self.GUID.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')

    async def read_bytes(self, num):
        return await self.reader.read(num)

    async def read_next_message(self):
        _logger.debug(f"Read next websocket[{self.ws_request.path}] message")
        try:
            b1, b2 = await self.read_bytes(2)
        except ConnectionResetError as e:
            _logger.info("Client closed connection.")
            self.keep_alive = False
            self.close_reason = "Client closed connection."
            return
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                _logger.info("Client closed connection.")
                self.keep_alive = False
                self.close_reason = "Client closed connection."
                return
            b1, b2 = 0, 0
        except ValueError as e:
            b1, b2 = 0, 0

        fin = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if opcode == OPCODE_CLOSE_CONN:
            _logger.info("Client asked to close connection.")
            self.keep_alive = False
            self.close_reason = "Client asked to close connection."
            return
        if not masked:
            _logger.warn("Client must always be masked.")
            self.keep_alive = False
            self.close_reason = "Client is not masked."
            return
        if opcode not in (OPCODE_TEXT, OPCODE_PING, OPCODE_PONG, OPCODE_CONTINUATION, OPCODE_BINARY):
            _logger.warn(f"Unknown opcode {opcode}.")
            self.keep_alive = False
            self.close_reason = f"Unknown opcode {opcode}."
            return

        if payload_length == 126:
            hb = await self.reader.read(2)
            payload_length = struct.unpack(">H", hb)[0]
        elif payload_length == 127:
            qb = await self.reader.read(8)
            payload_length = struct.unpack(">Q", qb)[0]

        masks = await self.read_bytes(4)
        frame_bytes = bytearray()
        payload = await self.read_bytes(payload_length)
        for encoded_byte in payload:
            frame_bytes.append(encoded_byte ^ masks[len(frame_bytes) % 4])

        if fin and opcode != OPCODE_CONTINUATION:
            # A normal frame, handle message.
            await self.on_message(opcode, frame_bytes)
            return

        if not fin and opcode != OPCODE_CONTINUATION:
            # Fragment message: first frame, try to create a cache object.
            if self._continution_cache is not None:
                # Check if another fragment message is being read.
                _logger.warning("Another continution message is not yet finished. Close connection for this error!")
                self.keep_alive = False
                self.close_reason = "Another continuation message is not yet finished. "
                return
            self._continution_cache = _ContinuationMessageCache(opcode)

        if self._continution_cache is None:
            # When the first frame is not send, all the other frames are ignored.
            _logger.warning("A continuation fragment frame is received, but the start fragment is not received yet, ignore this frame.")
            return

        await self.on_continuation_frame(self._continution_cache.opcode, bool(fin), frame_bytes)

        if fin:
            # Fragment message: end of this message.
            if self._continution_cache.message_bytes:
                await self.on_message(self._continution_cache.opcode, self._continution_cache.message_bytes)
            self._continution_cache = None

    def send_message(self, message: Union[bytes, str]):
        if isinstance(message, bytes):
            self.send_bytes(OPCODE_TEXT, message)
        elif isinstance(message, str):
            self.send_text(message)
        else:
            _logger.error(f"Cannot send message[{message}. ")

    def send_ping(self, message: Union[str, bytes]):
        if isinstance(message, bytes):
            self.send_bytes(OPCODE_PING, message)
        elif isinstance(message, str):
            self.send_bytes(OPCODE_PING, self._encode_to_UTF8(message))

    def send_pong(self, message: Union[str, bytes]):
        if isinstance(message, bytes):
            self.send_bytes(OPCODE_PONG, message)
        elif isinstance(message, str):
            self.send_bytes(OPCODE_PONG, self._encode_to_UTF8(message))

    def send_text(self, message: str):
        payload = self._encode_to_UTF8(message)
        self.send_bytes(OPCODE_TEXT, payload)

    def send_bytes(self, opcode, payload: bytes):
        header = bytearray()
        payload_length = len(payload)

        # Normal payload
        if payload_length <= 125:
            header.append(FIN | opcode)
            header.append(payload_length)

        # Extended payload
        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))

        # Huge extended payload
        elif payload_length < 18446744073709551616:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))

        else:
            raise Exception(
                "Message is too big. Consider breaking it into chunks.")

        self.request_writer.send(header + payload)

    def close(self, reason: str = ""):
        self.send_bytes(OPCODE_CLOSE_CONN, self._encode_to_UTF8(reason))
        self.keep_alive = False
        self.close_reason = "Server asked to close connection."

    def _encode_to_UTF8(self, data: str) -> bytes:
        try:
            return data.encode('UTF-8')
        except UnicodeEncodeError as e:
            _logger.error("Could not encode data to UTF-8 -- %s" % e)
            return f'{data}'.encode('UTF-8')
        except Exception as e:
            raise(e)

    def _try_decode_UTF8(self, data: str):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return False
        except Exception as e:
            raise(e)


class WebsocketSessionImpl(WebsocketSession):

    def __init__(self, handler: WebsocketRequestHandler, request: WebsocketRequest) -> None:
        self.__id = uuid4().hex
        self.__handler = handler
        self.__request = request

    @property
    def id(self):
        return self.__id

    @property
    def request(self):
        return self.__request

    @property
    def is_closed(self):
        return not self.__handler.keep_alive

    def send_ping(self, message: str):
        self.__handler.send_ping(message)

    def send_pone(self, message: str):
        self.__handler.send_pong(message)

    def send(self, message: str):
        self.__handler.send_message(message)

    def send_text(self, message: str):
        self.__handler.send_message(message)

    def send_binary(self, binary: bytes):
        self.__handler.send_bytes(OPCODE_BINARY, binary)

    def close(self, reason: str):
        self.__handler.close(reason)
