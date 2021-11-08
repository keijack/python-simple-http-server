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
import simple_http_server.__utils as utils

from typing import Any, Dict, List
from http import HTTPStatus
from .http_request_handler import HTTPRequestHandler
from .logger import get_logger

_logger = get_logger("simple_http_server.wsgi_request_server")


class WSGIRequestHandler:

    res_code_msg = {
        v: (v.phrase, v.description)
        for v in HTTPStatus.__members__.values()
    }

    def __init__(self, routing_conf, environment, start_response) -> None:
        self.env: Dict[str, str] = environment
        self.start_response = start_response

        self.status = "200 OK"
        self.__res_headers: Dict[str, List[str]] = {}
        self.response_headers = []
        self.body = []

        self.routing_conf = routing_conf
        self.headers = self._parse_headers()
        self.query_parameters = utils.decode_query_string(self.query_string)
        self.writer = self
        self.reader = self

    @property
    def rfile(self):
        if 'wsgi.input' in self.env:
            return self.env['wsgi.input']
        else:
            return None

    @property
    def command(self):
        return self.env['REQUEST_METHOD']

    @property
    def request_path(self):
        path = self.env['PATH_INFO']
        if path.startswith('/'):
            path = path[1:]
        return path

    @property
    def query_string(self):
        return self.env['QUERY_STRING']

    @property
    def request(self):
        return self

    # Wrapper method for readline
    async def readline(self):
        if self.rfile:
            return self.rfile.readline()
        else:
            return b""

    async def read(self, n: int = -1):
        if self.rfile:
            return self.rfile.read(n)
        else:
            return b''

    def write(self, data: bytes):
        if isinstance(self.body, list):
            self.body.append(data)
        else:
            self.body = [self.body, data]

    def write_eof(self):
        pass

    async def handle_request(self) -> List[bytes]:
        handler = HTTPRequestHandler(self, environment=self.env)
        await handler.handle_request()
        self.start_response(self.status, self.response_headers)
        return self.body

    def send_header(self, key, val):
        if key not in self.__res_headers:
            self.__res_headers[key] = [val]
        else:
            self.__res_headers[key].append(val)

    def end_headers(self):
        for k, vals in self.__res_headers.items():
            if k.lower() == 'connection':
                continue
            for val in vals:
                self.response_headers.append((k, str(val)))

    def _parse_headers(self):
        headers = {}
        if 'CONTENT_TYPE' in self.env and self.env['CONTENT_TYPE']:
            headers['Content-Type'] = self.env['CONTENT_TYPE']
        if 'CONTENT_LENGTH' in self.env and self.env['CONTENT_LENGTH']:
            headers['Content-Length'] = self.env['CONTENT_LENGTH']
        for k, v in self.env.items():
            if k.startswith("HTTP_"):
                header_name = k.replace("HTTP_", "")
                header_name = "-".join([p[0].upper() + p[1:].lower()
                                       for p in header_name.split("_")])
                headers[header_name] = v
        return headers

    def send_response(self, code, message=None):
        self.send_response_only(code, message)
        self.send_header('Date', utils.date_time_string())

    def send_response_only(self, code, message=None):
        if message is None:
            if code in self.res_code_msg:
                message = self.res_code_msg[code][0]
            else:
                message = ''
        self.status = f"{code} {message}"

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
