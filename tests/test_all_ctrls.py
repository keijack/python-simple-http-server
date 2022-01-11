# coding: utf-8

import os
import json
import websocket
import unittest
import urllib.request
import urllib.error
import http.client
from typing import Dict
from threading import Thread
from time import sleep

from simple_http_server.logger import get_logger, set_level
import simple_http_server.server as server

set_level("DEBUG")

_logger = get_logger("http_test")


class ThreadingServerTest(unittest.TestCase):

    PORT = 9090

    WAIT_COUNT = 10

    COROUTINE = False

    @classmethod
    def start_server(clz):
        _logger.info("start server in background. ")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server.scan(project_dir=root, base_dir="tests/ctrls",
                    regx=r'.*controllers.*')
        server.start(
            port=clz.PORT,
            resources={"/public/*": f"{root}/tests/static"},
            prefer_coroutine=clz.COROUTINE)

    @classmethod
    def setUpClass(clz):
        Thread(target=clz.start_server, daemon=True, name="t").start()
        retry = 0
        while not server.is_ready():
            sleep(1)
            retry = retry + 1
            _logger.info(
                f"server is not ready wait. {retry}/{clz.WAIT_COUNT} ")
            if retry >= clz.WAIT_COUNT:
                raise Exception("Server start wait timeout.")

    @classmethod
    def tearDownClass(clz):
        try:
            server.stop()
        except:
            pass

    @classmethod
    def visit(clz, ctx_path, headers: Dict[str, str] = {}, data=None, return_type: str = "TEXT"):
        req: urllib.request.Request = urllib.request.Request(
            f"http://127.0.0.1:{clz.PORT}/{ctx_path}")
        for k, v in headers.items():
            req.add_header(k, v)
        res: http.client.HTTPResponse = urllib.request.urlopen(req, data=data)

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

    def test_header_echo(self):
        res: http.client.HTTPResponse = self.visit(
            f"header_echo", headers={"X-KJ-ABC": "my-headers"}, return_type="RESPONSE")
        assert "X-Kj-Abc" in res.headers
        assert res.headers["X-Kj-Abc"] == "my-headers"

    def test_static(self):
        txt = self.visit("public/a.txt")
        assert txt == "hello world!"

    def test_path_value(self):
        pval = "abc"
        path_val = "xyz"
        txt = self.visit(f"path_values/{pval}/{path_val}/x")
        assert txt == f"<html><body>{pval}, {path_val}</body></html>"

    def test_error(self):
        try:
            self.visit("error")
        except urllib.error.HTTPError as err:
            assert err.code == 400
            error_msg = err.read().decode("utf-8")
            _logger.info(error_msg)
            assert error_msg == "code：400, message: Parameter Error!, explain: Test Parameter Error!"

    def test_coroutine(self):
        txt = self.visit(f"%E4%B8%AD%E6%96%87/coroutine?hey=KJ2")
        assert txt == "Success! KJ2"

    def test_post_json(self):
        data_dict = {
            "code": 0,
            "msg": "xxx"
        }
        res: str = self.visit(f"post_json", headers={"Content-Type": "application/json"}, data=json.dumps(data_dict).encode())
        res_dict: dict = json.loads(res)
        assert data_dict["code"] == res_dict["code"]
        assert data_dict["msg"] == res_dict["msg"]

    def test_filter(self):
        res: http.client.HTTPResponse = self.visit(
            f"tuple?user_name=kj&pass=wu", return_type="RESPONSE")
        assert "Res-Filter-Header" in res.headers
        assert res.headers["Res-Filter-Header"] == "from-filter"

    def test_exception(self):
        try:
            self.visit("exception")
        except urllib.error.HTTPError as err:
            assert err.code == 500
            error_msg = err.read().decode("utf-8")
            _logger.info(error_msg)
            assert error_msg == '500-Internal Server Error-some error occurs!'

    def test_ws(self):
        ws = websocket.WebSocket()
        path_val = "test"
        msg = "hello websocket!"
        ws.connect(f"ws://127.0.0.1:{self.PORT}/ws/{path_val}")
        ws.send(msg)
        txt = ws.recv()
        ws.close()
        assert txt == f"{path_val}-{msg}"


class CoroutineServerTest(ThreadingServerTest):

    COROUTINE = True
