# coding: utf-8

import os
import websocket
import unittest
from threading import Thread
from time import sleep
import urllib.request
import http.client

from simple_http_server.logger import get_logger, set_level
import simple_http_server.server as server

set_level("DEBUG")

_logger = get_logger("http_test")


class HttpRequestTest(unittest.TestCase):

    PORT = 9090

    WAIT_COUNT = 10

    @classmethod
    def start_server(clz):
        _logger.info("start server in background. ")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server.scan(project_dir=root, base_dir="tests/ctrls", regx=r'.*controllers.*')
        server.start(
            port=clz.PORT,
            resources={"/public/*": f"{root}/tests/static"})

    @classmethod
    def setUpClass(clz):
        Thread(target=clz.start_server, daemon=False, name="t").start()
        retry = 0
        while not server.is_ready():
            sleep(1)
            retry = retry + 1
            _logger.info(f"server is not ready wait. {retry}/{clz.WAIT_COUNT} ")
            if retry >= clz.WAIT_COUNT:
                raise Exception("Server start wait timeout.")

    @classmethod
    def tearDownClass(clz):
        try:
            server.stop()
        except:
            pass

    @classmethod
    def visit(clz, ctx_path, data=None, return_type: str = "TEXT"):
        res: http.client.HTTPResponse = urllib.request.urlopen(f"http://127.0.0.1:{clz.PORT}/{ctx_path}", data=data)

        if return_type == "RESPONSE":
            return res
        elif return_type == "HEADERS":
            headers = res.headers
            res.close()
            return headers
        else:
            txt = res.read().decode("utf-8")
            res.close()
            return txt

    def test_static(self):
        txt = self.visit("public/a.txt")
        assert txt == "hello world!"

    def test_path_value(self):
        pval = "abc"
        path_val = "xyz"
        txt = self.visit(f"path_values/{pval}/{path_val}/x")
        assert txt == f"<html><body>{pval}, {path_val}</body></html>"

    def test_ws(self):
        ws = websocket.WebSocket()
        path_val = "test"
        msg = "hello websocket!"
        ws.connect(f"ws://127.0.0.1:{self.PORT}/ws/{path_val}")
        ws.send(msg)
        txt = ws.recv()
        ws.close()
        assert txt == f"{path_val}-{msg}"
