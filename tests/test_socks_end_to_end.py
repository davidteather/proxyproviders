"""Sends a real request through a local SOCKS5 proxy using Proxy.format().

Everything runs on localhost: a tiny HTTP server is the target and a minimal SOCKS5
server (username/password auth, CONNECT only) is the proxy. This proves the formatted
output is something requests actually routes through the proxy, not just a string that
looks right.
"""

import http.server
import select
import socket
import socketserver
import struct
import threading

import pytest
import requests

from proxyproviders import Proxy, ProxyFormat

pytest.importorskip("socks", reason="needs requests[socks]")

USERNAME = "user-country-us"
PASSWORD = "p#ss/w@rd"


class _Target(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello through the proxy"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _Socks5Handler(socketserver.BaseRequestHandler):
    def _read(self, n):
        data = b""
        while len(data) < n:
            chunk = self.request.recv(n - len(data))
            if not chunk:
                raise ConnectionError("client closed")
            data += chunk
        return data

    def handle(self):
        # Greeting: only username/password auth (0x02) is offered back
        _, n_methods = self._read(2)
        self._read(n_methods)
        self.request.sendall(b"\x05\x02")

        # Username/password sub-negotiation (RFC 1929)
        self._read(1)
        username = self._read(self._read(1)[0]).decode()
        password = self._read(self._read(1)[0]).decode()
        self.server.seen_credentials.append((username, password))
        if (username, password) != (USERNAME, PASSWORD):
            self.request.sendall(b"\x01\x01")
            return
        self.request.sendall(b"\x01\x00")

        # CONNECT request
        _, command, _, address_type = self._read(4)
        if address_type == 1:
            host = socket.inet_ntoa(self._read(4))
        elif address_type == 3:
            host = self._read(self._read(1)[0]).decode()
        else:
            return
        port = struct.unpack("!H", self._read(2))[0]
        if command != 1:
            return

        upstream = socket.create_connection((host, port))
        self.server.connections.append((host, port))
        self.request.sendall(b"\x05\x00\x00\x01" + bytes(4) + bytes(2))

        try:
            while True:
                readable, _, _ = select.select([self.request, upstream], [], [], 5)
                if not readable:
                    break
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is self.request else self.request).sendall(data)
        finally:
            upstream.close()


class _ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


@pytest.fixture
def target():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Target)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def socks_server():
    server = _ThreadingServer(("127.0.0.1", 0), _Socks5Handler)
    server.seen_credentials = []
    server.connections = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def socks_proxy(server, password=PASSWORD):
    return Proxy(
        id="local-socks",
        username=USERNAME,
        password=password,
        proxy_address="127.0.0.1",
        port=server.server_address[1],
        protocols=["socks5"],
    )


def test_requests_goes_through_the_socks_proxy(target, socks_server):
    url = f"http://127.0.0.1:{target.server_address[1]}/"
    proxies = socks_proxy(socks_server).format(ProxyFormat.REQUESTS)

    session = requests.Session()
    session.trust_env = False
    response = session.get(url, proxies=proxies, timeout=10)

    assert response.text == "hello through the proxy"
    # The request reached the target through the proxy, with the exact credentials,
    # including the characters that need percent-encoding in a URL
    assert socks_server.connections == [("127.0.0.1", target.server_address[1])]
    assert socks_server.seen_credentials == [(USERNAME, PASSWORD)]


def test_wrong_password_is_rejected_by_the_proxy(target, socks_server):
    """Shows the request really depends on the proxy: bad credentials fail it."""
    url = f"http://127.0.0.1:{target.server_address[1]}/"
    proxies = socks_proxy(socks_server, password="wrong").format(ProxyFormat.REQUESTS)

    session = requests.Session()
    session.trust_env = False
    with pytest.raises(requests.exceptions.ConnectionError):
        session.get(url, proxies=proxies, timeout=10)

    assert socks_server.connections == []
