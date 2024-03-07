# -*- coding: utf-8 -*-


import os
import shutil
from uuid import uuid4
from naja_atra import WebsocketCloseReason, WebsocketHandler, WebsocketRequest, WebsocketSession, websocket_handler, websocket_message, websocket_handshake, websocket_open, websocket_close, WEBSOCKET_MESSAGE_TEXT
import naja_atra.utils.logger as logger

_logger = logger.get_logger("ws_test")


@websocket_handler(endpoint="/ws/{path_val}")
class WSHandler(WebsocketHandler):

    def __init__(self) -> None:
        self.uuid: str = uuid4().hex

    def on_handshake(self, request: WebsocketRequest):
        return 0, {}

    async def on_open(self, session: WebsocketSession):

        _logger.info(f">>{session.id}<< open! {session.request.path_values}")

    def on_text_message(self, session: WebsocketSession, message: str):
        _logger.info(
            f">>{session.id}::{self.uuid}<< on text message: {message}")
        session.send(f"{session.request.path_values['path_val']}-{message}")
        if message == "close":
            session.close()

    def on_close(self, session: WebsocketSession, reason: WebsocketCloseReason):
        _logger.info(
            f">>{session.id}<< close::{reason.message}-{reason.code}-{reason.reason}")

    def on_binary_frame(self, session: WebsocketSession = None, fin: bool = False, frame_data: bytes = b''):
        _logger.info(f"Fin => {fin}, Data: {frame_data}")
        return True

    def on_binary_message(self, session: WebsocketSession = None, message: bytes = b''):
        _logger.info(f'Binary Message:: {message}')
        tmp_folder = os.path.dirname(os.path.abspath(__file__)) + "/tmp"
        is_dir_tmp_folder = os.path.isdir(tmp_folder)
        if not is_dir_tmp_folder:
            os.mkdir(tmp_folder)
        session.send(
            'binary-message-received, and this is some message for the long size.', chunk_size=10)
        tmp_file_path = f"{tmp_folder}/ws_bi_re.tmp"
        with open(tmp_file_path, 'wb') as out_file:
            out_file.write(message)

        session.send_file(tmp_file_path)
        session.send_file(tmp_file_path, chunk_size=10)
        if is_dir_tmp_folder:
            os.remove(tmp_file_path)
        else:
            shutil.rmtree(tmp_folder)


@websocket_handler(regexp="^/ws-reg/([a-zA-Z0-9]+)$", singleton=False)
class WSRegHander(WebsocketHandler):

    def __init__(self) -> None:
        self.uuid: str = uuid4().hex

    def on_text_message(self, session: WebsocketSession, message: str):
        _logger.info(
            f">>{session.id}::{self.uuid}<< on text message: {message}")
        _logger.info(f"{session.request.reg_groups}")
        session.send(f"{session.request.reg_groups[0]}-{message}")


@websocket_handshake(endpoint="/ws-fun/{path_val}")
def ws_handshake(request: WebsocketRequest):
    return 0, {}


@websocket_open(endpoint="/ws-fun/{path_val}")
def ws_open(session: WebsocketSession):
    _logger.info(f">>{session.id}<< open! {session.request.path_values}")


@websocket_close(endpoint="/ws-fun/{path_val}")
def ws_close(session: WebsocketSession, reason: WebsocketCloseReason):
    _logger.info(
        f">>{session.id}<< close::{reason.message}-{reason.code}-{reason.reason}")


@websocket_message(endpoint="/ws-fun/{path_val}", message_type=WEBSOCKET_MESSAGE_TEXT)
async def ws_text(session: WebsocketSession, message: str):
    _logger.info(f">>{session.id}<< on text message: {message}")
    session.send(f"{session.request.path_values['path_val']}-{message}")
    if message == "close":
        session.close()
