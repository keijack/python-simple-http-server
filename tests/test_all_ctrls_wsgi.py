# coding: utf-8

import os
from typing import Dict
import unittest
from threading import Thread
from time import sleep
import urllib.request
import urllib.error
import http.client

from wsgiref.simple_server import WSGIServer, make_server
from simple_http_server.logger import get_logger, set_level
import simple_http_server.server as server


set_level("DEBUG")

_logger = get_logger("wsgi_test")


class WSGIHttpRequestTest(unittest.TestCase):

    PORT = 9092

    WAIT_COUNT = 10

    httpd: WSGIServer = None

    server_ready = False

    @classmethod
    def start_server(cls):
        _logger.info("start server in background. ")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server.scan(project_dir=root, base_dir="tests/ctrls", regx=r'.*controllers.*')
        wsgi_proxy = server.init_wsgi_proxy(resources={"/public/*": f"{root}/tests/static"})

        def wsgi_simple_app(environment, start_response):
            return wsgi_proxy.app_proxy(environment, start_response)
        cls.httpd = make_server("", cls.PORT, wsgi_simple_app)
        cls.server_ready = True
        cls.httpd.serve_forever()

    @classmethod
    def setUpClass(cls):
        Thread(target=cls.start_server, daemon=False, name="t").start()
        retry = 0
        while not cls.server_ready:
            sleep(1)
            retry = retry + 1
            _logger.info(f"server is not ready wait. {retry}/{cls.WAIT_COUNT} ")
            if retry >= cls.WAIT_COUNT:
                raise Exception("Server start wait timeout.")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
        except:
            pass

    @classmethod
    def visit(cls, ctx_path, headers: Dict[str, str] = {}, data=None, return_type: str = "TEXT"):
        req: urllib.request.Request = urllib.request.Request(f"http://127.0.0.1:{cls.PORT}/{ctx_path}")
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
        res: http.client.HTTPResponse = self.visit(f"header_echo", headers={"X-KJ-ABC": "my-headers"}, return_type="RESPONSE")
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

    def test_exception(self):
        try:
            self.visit("exception")
        except urllib.error.HTTPError as err:
            assert err.code == 500
            error_msg = err.read().decode("utf-8")
            _logger.info(error_msg)
            assert error_msg == '500-Internal Server Error-some error occurs!'
