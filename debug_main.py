# -*- coding: utf-8 -*-
#
# If you want to run this file, please install following package to run.
# python3 -m pip install werkzeug 'uvicorn[standard]'
#

from naja_atra import request_map
import naja_atra.server as server

import os
import signal


from naja_atra.http_servers.http_server import HttpServer
from naja_atra.utils.logger import get_logger, set_level

from naja_atra import get_app_conf
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


def on_sig_term(signum, frame):
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
