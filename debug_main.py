# -*- coding: utf-8 -*-
#
# If you want to run this file, please install following package to run.
# python3 -m pip install werkzeug 'uvicorn[standard]'
#

from simple_http_server import request_map
from wsgiref.simple_server import WSGIServer, make_server
import simple_http_server.server as server
from simple_http_server.server import ASGIProxy
import os
import signal
import asyncio

import uvicorn

from threading import Thread
from time import sleep
from simple_http_server.__main__ import main
from simple_http_server.http_server import HttpServer
from simple_http_server.logger import get_logger, set_level

from werkzeug.serving import make_server as mk_server

from simple_http_server import get_app_conf
set_level("DEBUG")


@request_map("/stop")
def stop():
    server.stop()
    return "<!DOCTYPE html><html><head><title>关闭</title></head><body>关闭成功！</body></html>"


_logger = get_logger("http_test")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

_server: HttpServer = None

app = get_app_conf("2")


@app.route("/")
def idx():
    return {"msg": "hello, world!"}


def start_via_class():
    global _server

    _server = HttpServer(host=('', 9091),
                         resources={"/p/**": f"{PROJECT_ROOT}/tests/static"},
                         app_conf=app)
    _server.start()


def start_server():
    _logger.info("start server in background. ")

    server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
    server.start(
        # port=9443,
        port=9090,
        resources={"/public/*": f"{PROJECT_ROOT}/tests/static",
                   "/*": f"{PROJECT_ROOT}/tests/static",
                   '/inn/**': f"{PROJECT_ROOT}/tests/static",
                   '**.txt': f"{PROJECT_ROOT}/tests/static",
                   '*.ini': f"{PROJECT_ROOT}/tests/static",
                   },
        # ssl=True,
        # certfile=f"{PROJECT_ROOT}/tests/certs/fullchain.pem",
        # keyfile=f"{PROJECT_ROOT}/tests/certs//privkey.pem",
        gzip_content_types={"image/x-icon", "text/plain"},
        gzip_compress_level=9,
        prefer_coroutine=False)


wsgi_server: WSGIServer = None


def start_server_wsgi():
    _logger.info("start server in background. ")
    server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
    wsgi_proxy = server.init_wsgi_proxy(
        resources={"/public/*": f"{PROJECT_ROOT}/tests/static",
                   "/*": f"{PROJECT_ROOT}/tests/static"})

    global wsgi_server
    wsgi_server = make_server("", 9090, wsgi_proxy.app_proxy)
    wsgi_server.serve_forever()


def start_server_werkzeug():
    server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
    wsgi_proxy = server.init_wsgi_proxy(
        resources={"/public/*": f"{PROJECT_ROOT}/tests/static",
                   "/*": f"{PROJECT_ROOT}/tests/static"})

    global wsgi_server
    wsgi_server = mk_server("", 9090, wsgi_proxy.app_proxy)
    wsgi_server.serve_forever()


asgi_server: uvicorn.Server = None

asgi_proxy: ASGIProxy = None
init_asgi_proxy_lock: asyncio.Lock = asyncio.Lock()


async def init_asgi_proxy():
    global asgi_proxy
    if asgi_proxy == None:
        async with init_asgi_proxy_lock:
            if asgi_proxy == None:
                _logger.info("init asgi proxy... ")
                server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
                asgi_proxy = server.init_asgi_proxy(
                    resources={"/public/*": f"{PROJECT_ROOT}/tests/static",
                               "/*": f"{PROJECT_ROOT}/tests/static"})


async def asgi_app(scope, receive, send):
    await init_asgi_proxy()
    await asgi_proxy.app_proxy(scope, receive, send)


def start_server_uvicorn():
    config = uvicorn.Config("debug_main:asgi_app",
                            host="0.0.0.0", port=9090, log_level="info")
    global asgi_server
    asgi_server = uvicorn.Server(config)
    asgi_server.run()


def on_sig_term(signum, frame):
    if wsgi_server:
        _logger.info(f"Receive signal [{signum}], shutdown the wsgi server...")
        Thread(target=wsgi_server.shutdown).start()
    elif asgi_server:
        _logger.info(f"Receive signal [{signum}], shutdown the wsgi server...")
        Thread(target=asgi_server.shutdown).start()
    else:
        _logger.info(f"Receive signal [{signum}], stop server now...")
        server.stop()
    if _server:
        _server.shutdown()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, on_sig_term)
    signal.signal(signal.SIGINT, on_sig_term)
    # Thread(target=start_via_class, daemon=True).start()
    # sleep(1)
    # start_via_class()
    # main(sys.argv[1:])
    start_server()
    # start_server_wsgi()
    # start_server_werkzeug()
    # start_server_uvicorn()
