
import os
import sys
import signal
import getopt
from . import server
from .utils import logger

_logger = logger.get_logger("naja_atra.__main__")


def print_help():
    print("""
    python3 -m naja_atra [options]

    Options:
    -h    --help        Show this message and exit.
    -p    --port        Specify alternate port (default: 9090)
    -b    --bind        Specify alternate bind address (default: all interfaces)
    -s    --scan        Scan this path to find controllers, if absent, will scan the current work directory
          --regex       Only import the files that macthes this regular expresseion.
    -r    --resources   Specify the resource directory
          --loglevel    Specify log level (default: info)
    """)


def on_sig_term(signum, frame):
    _logger.info(f"Receive signal [{signum}], stop server now...")
    server.stop()


def main(argv):
    try:
        opts = getopt.getopt(argv, "p:b:s:r:h",
                             ["port=", "bind=", "scan=", "resources=", "regex=", "loglevel=", "help"])[0]
        opts = dict(opts)
        if "-h" in opts or "--help" in opts:
            print_help()
            return
        port = int(opts.get("-p", opts.get("--port", "9090")))
        scan_path = opts.get("-s", opts.get("--scan", os.getcwd()))
        regex = opts.get("--regex", "")
        res_dir = opts.get("-r", opts.get("--resources", ""))
        binding_host = opts.get("-b", opts.get("--bind", "0.0.0.0"))
        log_level = opts.get("--loglevel", "")

        if log_level:
            logger.set_level(log_level)
        signal.signal(signal.SIGTERM, on_sig_term)
        signal.signal(signal.SIGINT, on_sig_term)
        server.scan(regx=regex, project_dir=scan_path)
        server.start(
            host=binding_host,
            port=port,
            resources={"/**": res_dir},
            keep_alive=False,
            prefer_coroutine=False)
    except Exception as e:
        print(f"Start server error: {e}")
        print_help()


if __name__ == "__main__":
    main(sys.argv[1:])
