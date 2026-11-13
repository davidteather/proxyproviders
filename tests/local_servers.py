"""Tiny servers that run on localhost so tests can send real traffic through a proxy.

``TargetServer`` is the site being requested. ``HttpProxyServer`` is a forward proxy
with basic auth that records what passed through it. Nothing here leaves the machine.
"""

import base64
import http.client
import http.server
import socket
import threading
import time
from typing import List, Optional
from urllib.parse import urlsplit

from proxyproviders import Proxy

BODY = b"hello through the proxy"


class _TargetHandler(http.server.BaseHTTPRequestHandler):
    def _respond(self):
        self.server.hits.append((self.command, self.path))
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(BODY)

    do_GET = do_POST = do_HEAD = _respond

    def log_message(self, *args):
        pass


class _ProxyHandler(http.server.BaseHTTPRequestHandler):
    def _forward(self):
        server = self.server
        expected = base64.b64encode(
            f"{server.username}:{server.password}".encode()
        ).decode()
        if self.headers.get("Proxy-Authorization") != f"Basic {expected}":
            server.rejected.append(self.path)
            self.send_response(407)
            self.send_header("Proxy-Authenticate", 'Basic realm="proxy"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        server.requests.append((self.command, self.path))
        if server.behaviour == "hang":
            # Accepts the request and never answers, like a stalled proxy
            time.sleep(5)
            self.close_connection = True
            return
        if server.forced_status is not None:
            self.send_response(server.forced_status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        target = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        upstream = http.client.HTTPConnection(target.hostname, target.port, timeout=10)
        try:
            upstream.request(self.command, target.path or "/", body=body)
            response = upstream.getresponse()
            payload = response.read()
        finally:
            upstream.close()

        if server.behaviour == "drop_after_relay":
            # The target has handled the request, but the client never hears back
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            return

        self.send_response(response.status)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_HEAD = _forward

    def log_message(self, *args):
        pass


class _Server:
    handler = None

    def __init__(self):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        threading.Thread(
            target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
        ).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TargetServer(_Server):
    handler = _TargetHandler

    def __init__(self):
        super().__init__()
        self.httpd.hits = []
        self.url = f"http://127.0.0.1:{self.port}/"

    @property
    def hits(self) -> List[tuple]:
        return self.httpd.hits


class HttpProxyServer(_Server):
    """A forward proxy for plain-HTTP targets that requires basic auth."""

    handler = _ProxyHandler

    def __init__(
        self,
        username: str = "user-country-us",
        password: str = "p#ss/w@rd",
        forced_status: Optional[int] = None,
        behaviour: Optional[str] = None,
    ):
        super().__init__()
        self.httpd.behaviour = behaviour
        self.httpd.username = username
        self.httpd.password = password
        self.httpd.forced_status = forced_status
        self.httpd.requests = []
        self.httpd.rejected = []

    @property
    def requests(self) -> List[tuple]:
        """Requests that passed authentication and went through this proxy."""
        return self.httpd.requests

    @property
    def rejected(self) -> List[str]:
        """Requests turned away with 407 for missing or wrong credentials."""
        return self.httpd.rejected

    def proxy(self, **overrides) -> Proxy:
        fields = {
            "id": f"local-{self.port}",
            "username": self.httpd.username,
            "password": self.httpd.password,
            "proxy_address": "127.0.0.1",
            "port": self.port,
            "protocols": ["http", "https"],
        }
        fields.update(overrides)
        return Proxy(**fields)


def dead_proxy() -> Proxy:
    """A proxy on a port nothing is listening on, so connecting to it is refused."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return Proxy(
        id=f"dead-{port}",
        username="user",
        password="pass",
        proxy_address="127.0.0.1",
        port=port,
        protocols=["http", "https"],
    )
