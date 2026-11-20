"""Serve the delivery folder for the local review console."""
import argparse
import functools
import http.server
import socket
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REL = "versions/v0.6-mt/review/"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def free_port(start=18789):
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--port", type=int, default=18789)
    args = ap.parse_args()
    port = free_port(args.port)
    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/{REL}"
    print(f"serving {ROOT} at {url}")
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
