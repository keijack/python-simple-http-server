
import os
import signal
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


def start_server():
    _logger.info("start server in background. ")
    root = os.path.dirname(os.path.abspath(__file__))
    server.scan(base_dir="tests/ctrls",
                regx=r'.*controllers.*')
    print(root)
    server.start(
        port=9443,
        resources={"/public/*": f"{root}/tests/static"},
        ssl=True,
        certfile=f"{root}/tests/certs/fullchain.pem",
        keyfile=f"{root}/tests/certs//privkey.pem",
        prefer_coroutine=True)


def start_server_wsgi():
    _logger.info("start server in background. ")
    root = os.path.dirname(os.path.abspath(__file__))
    server.scan(base_dir="tests/ctrls", regx=r'.*controllers.*')
    wsgi_proxy = server.init_wsgi_proxy(
        resources={"/public/*": f"{root}/tests/static"})

    def wsgi_simple_app(environment, start_response):
        return wsgi_proxy.app_proxy(environment, start_response)
    httpd: WSGIServer = make_server("", 9090, wsgi_simple_app)
    httpd.serve_forever()


def on_sig_term(signum, frame):
    _logger.info(f"Receive signal [{signum}], stop server now...")
    server.stop()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, on_sig_term)
    signal.signal(signal.SIGINT, on_sig_term)

    start_server()
