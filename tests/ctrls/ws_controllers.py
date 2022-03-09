# -*- coding: utf-8 -*-


from email import message
from simple_http_server import WebsocketCloseReason, WebsocketHandler, WebsocketRequest, WebsocketSession, websocket_handler
import simple_http_server.logger as logger

_logger = logger.get_logger("ws_test")


@websocket_handler(endpoint="/ws/{path_val}")
class WSHandler(WebsocketHandler):

    def on_handshake(self, request: WebsocketRequest):
        return 0, {}

    async def on_open(self, session: WebsocketSession):

        _logger.info(f">>{session.id}<< open! {session.request.path_values}")

    def on_text_message(self, session: WebsocketSession, message: str):
        _logger.info(f">>{session.id}<< on text message: {message}")
        session.send(f"{session.request.path_values['path_val']}-{message}")

    def on_close(self, session: WebsocketSession, reason: WebsocketCloseReason):
        _logger.info(f">>{session.id}<< close::{reason.message}-{reason.code}-{reason.reason}")

    def on_binary_frame(self, session: WebsocketSession = None, fin: bool = False, frame_data: bytes = b''):
        _logger.info(f"Fin => {fin}, Data: {frame_data}")
        return True

    def on_binary_message(self, session: WebsocketSession = None, message: bytes = b''):
        _logger.info(f'Binary Message:: {message}')
        session.send(f'{message}')
