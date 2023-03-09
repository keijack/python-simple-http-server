
import os
import sys
import signal
import getopt
import simple_http_server.logger as logger
import simple_http_server.server as server

_logger = logger.get_logger("__main__")


def print_help():
    print("""
    python3 -m simple_http_server [options]

    Options:
    -h    --help        Show this message and exit.
    -p    --port        Specify alternate port (default: 9090)
    -b    --bind        Specify alternate bind address (default: all interfaces)
    -d    --directory   Specify alternate directory (default: current directory)
          --loglevel    Specify log level (default: info)
    """)


def on_sig_term(signum, frame):
    _logger.info(f"Receive signal [{signum}], stop server now...")
    server.stop()


def main(argv):
    try:
        opts = getopt.getopt(argv, "p:b:d:h",
                             ["port=", "bind=", "directory=", "loglevel=", "help"])[0]
        opts = dict(opts)
        if "-h" in opts or "--help" in opts:
            print_help()
            return
        port = int(opts.get("-p", opts.get("--port", "9090")))
        working_dir = opts.get("-d", opts.get("--directory", os.getcwd()))
        binding_host = opts.get("-b", opts.get("--bind", "0.0.0.0"))
        log_level = opts.get("--loglevel", "")

        if log_level:
            logger.set_level(log_level)
        signal.signal(signal.SIGTERM, on_sig_term)
        signal.signal(signal.SIGINT, on_sig_term)
        server.start(
            host=binding_host,
            port=port,
            resources={"/**": working_dir},
            keep_alive=False,
            prefer_coroutine=False)
    except Exception:
        print_help()


if __name__ == "__main__":
    main(sys.argv[1:])
