"""Each ProxyFormat is handed to the real client it is named after.

These tests send a request through a local authenticated proxy with the current release
of each library, so a client changing its proxy API (as httpx did when it dropped
``proxies=``) fails here instead of in a user's code. The proxy password contains
characters that only survive if the URL is percent-encoded correctly.
"""

import asyncio
import os
import shutil
import subprocess
import urllib.request

import pytest
import requests

from proxyproviders import ProxyFormat
from tests.local_servers import BODY


@pytest.fixture(autouse=True)
def no_proxy_environment(monkeypatch):
    """urllib and curl honour NO_PROXY, which would skip the local proxy under test."""
    for name in list(os.environ):
        if name.lower() in ("no_proxy", "http_proxy", "https_proxy", "all_proxy"):
            monkeypatch.delenv(name)


def assert_went_through(http_proxy, target, method="GET"):
    assert http_proxy.requests == [(method, target.url)]
    assert http_proxy.rejected == []
    assert len(target.hits) == 1


def test_requests(http_proxy, target):
    session = requests.Session()
    session.trust_env = False
    response = session.get(
        target.url, proxies=http_proxy.proxy().format(ProxyFormat.REQUESTS), timeout=10
    )
    assert response.content == BODY
    assert_went_through(http_proxy, target)


def test_urllib(http_proxy, target):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(http_proxy.proxy().format(ProxyFormat.URLLIB))
    )
    with opener.open(target.url, timeout=10) as response:
        assert response.read() == BODY
    assert_went_through(http_proxy, target)


def test_httpx(http_proxy, target):
    httpx = pytest.importorskip("httpx")
    with httpx.Client(
        proxy=http_proxy.proxy().format(ProxyFormat.HTTPX), trust_env=False
    ) as client:
        response = client.get(target.url, timeout=10)
    assert response.content == BODY
    assert_went_through(http_proxy, target)


def test_httpx_async(http_proxy, target):
    httpx = pytest.importorskip("httpx")

    async def fetch():
        async with httpx.AsyncClient(
            proxy=http_proxy.proxy().format(ProxyFormat.HTTPX), trust_env=False
        ) as client:
            return await client.get(target.url, timeout=10)

    assert asyncio.run(fetch()).content == BODY
    assert_went_through(http_proxy, target)


def test_aiohttp(http_proxy, target):
    aiohttp = pytest.importorskip("aiohttp")

    async def fetch():
        async with aiohttp.ClientSession() as session:
            async with session.get(
                target.url,
                proxy=http_proxy.proxy().format(ProxyFormat.AIOHTTP),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                return await response.read()

    assert asyncio.run(fetch()) == BODY
    assert_went_through(http_proxy, target)


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl is not installed")
class TestCurl:
    def run(self, args, env=None):
        clean = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
        return subprocess.run(
            ["curl", "--silent", "--show-error", "--max-time", "10", *args],
            capture_output=True,
            env={**clean, **(env or {})},
            check=False,
        )

    def test_curl_arguments(self, http_proxy, target):
        result = self.run(
            [*http_proxy.proxy().format(ProxyFormat.CURL), "--noproxy", "", target.url]
        )
        assert result.stdout == BODY, result.stderr
        assert_went_through(http_proxy, target)

    def test_environment_variables(self, http_proxy, target):
        """ProxyFormat.ENV is what a subprocess reads its proxy from."""
        env = http_proxy.proxy().format(ProxyFormat.ENV)
        result = self.run(["--noproxy", "", target.url], env=env)
        assert result.stdout == BODY, result.stderr
        assert_went_through(http_proxy, target)


def test_wrong_password_is_rejected(http_proxy, target):
    """The proxy really is checking credentials, so the tests above prove something."""
    session = requests.Session()
    session.trust_env = False
    response = session.get(
        target.url,
        proxies=http_proxy.proxy(password="wrong").format(ProxyFormat.REQUESTS),
        timeout=10,
    )
    assert response.status_code == 407
    assert http_proxy.rejected == [target.url]
    assert target.hits == []


def test_playwright_shape(http_proxy):
    """Playwright needs a browser to test for real, so only the shape is checked."""
    proxy = http_proxy.proxy()
    assert proxy.format(ProxyFormat.PLAYWRIGHT) == {
        "server": f"http://127.0.0.1:{proxy.port}",
        "username": proxy.username,
        "password": proxy.password,
    }
