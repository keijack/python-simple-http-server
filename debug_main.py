
import os
import signal
from threading import Thread
import simple_http_server.server as server


from wsgiref.simple_server import WSGIServer, make_server
from simple_http_server import request_map


from simple_http_server.logger import get_logger, set_level


@request_map("/stop")
def stop():
    server.stop()
    return "<!DOCTYPE html><html><head><title>关闭</title></head><body>关闭成功！</body></html>"


set_level("DEBUG")

_logger = get_logger("http_test")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def start_server():
    _logger.info("start server in background. ")
    server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
    server.start(
        port=9443,
        resources={"/public/*": f"{PROJECT_ROOT}/tests/static"},
        ssl=True,
        certfile=f"{PROJECT_ROOT}/tests/certs/fullchain.pem",
        keyfile=f"{PROJECT_ROOT}/tests/certs//privkey.pem",
        prefer_coroutine=True)


wsgi_server: WSGIServer = None


def start_server_wsgi():
    _logger.info("start server in background. ")
    server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
    wsgi_proxy = server.init_wsgi_proxy(
        resources={"/public/*": f"{PROJECT_ROOT}/tests/static"})

    global wsgi_server
    wsgi_server = make_server("", 9090, wsgi_proxy.app_proxy)
    wsgi_server.serve_forever()


def on_sig_term(signum, frame):
    if wsgi_server:
        _logger.info(f"Receive signal [{signum}], shutdown the wsgi server...")
        Thread(target=wsgi_server.shutdown).start()
    else:
        _logger.info(f"Receive signal [{signum}], stop server now...")
        server.stop()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, on_sig_term)
    signal.signal(signal.SIGINT, on_sig_term)

    start_server()
    # start_server_wsgi()
