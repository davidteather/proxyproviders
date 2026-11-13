"""The httpx rotating transports send real requests through local proxies."""

import asyncio

import pytest

from proxyproviders import ProxyList
from proxyproviders.algorithms import First
from tests.local_servers import BODY, dead_proxy

httpx = pytest.importorskip("httpx")

from proxyproviders.httpx_transport import (  # noqa: E402
    AsyncRotatingTransport,
    RotatingTransport,
)


def sync_get(transport, url, method="GET", **kwargs):
    with httpx.Client(transport=transport, timeout=10) as client:
        return client.request(method, url, **kwargs)


def async_get(transport, url, method="GET", **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=transport, timeout=10) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(run())


CASES = [
    pytest.param(RotatingTransport, sync_get, id="sync"),
    pytest.param(AsyncRotatingTransport, async_get, id="async"),
]


@pytest.mark.parametrize("transport_class, get", CASES)
class TestRotatingTransports:
    def test_each_request_uses_the_next_proxy(
        self, transport_class, get, make_http_proxy, target
    ):
        first, second = make_http_proxy(), make_http_proxy()
        provider = ProxyList([first.proxy(), second.proxy()])

        for _ in range(2):
            transport = transport_class(provider)
            assert get(transport, target.url).content == BODY

        assert len(first.requests) == len(second.requests) == 1

    def test_dead_proxy_is_retried_on_a_working_one(
        self, transport_class, get, http_proxy, target
    ):
        transport = transport_class(ProxyList([dead_proxy(), http_proxy.proxy()]))

        response = get(transport, target.url)

        assert response.content == BODY
        assert http_proxy.requests == [("GET", target.url)]
        assert transport.last_proxy.port == http_proxy.port
        assert transport.provider.available_proxies() == [http_proxy.proxy()]

    def test_post_is_retried_when_the_proxy_was_never_reached(
        self, transport_class, get, http_proxy, target
    ):
        transport = transport_class(ProxyList([dead_proxy(), http_proxy.proxy()]))

        response = get(transport, target.url, method="POST", content=b"a=1")

        assert response.content == BODY
        assert target.hits == [("POST", "/")]

    def test_raises_when_every_proxy_fails(self, transport_class, get, target):
        transport = transport_class(
            ProxyList([dead_proxy(), dead_proxy()]), max_retries=1
        )

        with pytest.raises(httpx.TransportError):
            get(transport, target.url)

        assert target.hits == []
        assert transport.provider.available_proxies() == []

    def test_max_retries_zero_does_not_retry(
        self, transport_class, get, http_proxy, target
    ):
        transport = transport_class(
            ProxyList([dead_proxy(), http_proxy.proxy()]), max_retries=0
        )

        with pytest.raises(httpx.TransportError):
            get(transport, target.url)

        assert http_proxy.requests == []

    def test_retry_statuses_moves_on_from_a_blocked_proxy(
        self, transport_class, get, make_http_proxy, target
    ):
        blocked, working = make_http_proxy(forced_status=403), make_http_proxy()
        transport = transport_class(
            ProxyList([blocked.proxy(), working.proxy()]), retry_statuses={403}
        )

        assert get(transport, target.url).status_code == 200
        assert len(blocked.requests) == len(working.requests) == 1
        assert transport.provider.available_proxies() == [working.proxy()]

    def test_status_is_returned_as_is_without_retry_statuses(
        self, transport_class, get, make_http_proxy, target
    ):
        blocked, working = make_http_proxy(forced_status=403), make_http_proxy()
        transport = transport_class(ProxyList([blocked.proxy(), working.proxy()]))

        assert get(transport, target.url).status_code == 403
        assert working.requests == []

    def test_last_response_is_returned_when_every_proxy_is_blocked(
        self, transport_class, get, make_http_proxy, target
    ):
        proxies = [make_http_proxy(forced_status=429).proxy() for _ in range(2)]
        transport = transport_class(
            ProxyList(proxies), retry_statuses={429}, max_retries=1
        )

        assert get(transport, target.url).status_code == 429

    def test_algorithm_is_passed_to_the_provider(
        self, transport_class, get, make_http_proxy, target
    ):
        first, second = make_http_proxy(), make_http_proxy()
        provider = ProxyList([first.proxy(), second.proxy()])

        for _ in range(3):
            get(transport_class(provider, algorithm=First()), target.url)

        assert len(first.requests) == 3
        assert second.requests == []

    def test_negative_max_retries_is_refused(self, transport_class, get):
        with pytest.raises(ValueError):
            transport_class(ProxyList(["203.0.113.1:8080"]), max_retries=-1)


def test_sync_client_reuses_one_transport_across_requests(make_http_proxy, target):
    first, second = make_http_proxy(), make_http_proxy()
    transport = RotatingTransport(ProxyList([first.proxy(), second.proxy()]))

    with httpx.Client(transport=transport, timeout=10) as client:
        for _ in range(4):
            assert client.get(target.url).content == BODY
        assert len(transport._transports) == 2

    assert len(first.requests) == len(second.requests) == 2
    assert transport._transports == {}  # closed with the client


def test_async_client_rotates_across_concurrent_requests(make_http_proxy, target):
    first, second = make_http_proxy(), make_http_proxy()
    transport = AsyncRotatingTransport(ProxyList([first.proxy(), second.proxy()]))

    async def run():
        async with httpx.AsyncClient(transport=transport, timeout=10) as client:
            return await asyncio.gather(*(client.get(target.url) for _ in range(6)))

    responses = asyncio.run(run())

    assert [r.content for r in responses] == [BODY] * 6
    assert len(first.requests) == len(second.requests) == 3
    assert transport._transports == {}


def test_streamed_body_is_not_retried(http_proxy, target):
    transport = RotatingTransport(ProxyList([dead_proxy(), http_proxy.proxy()]))

    def chunks():
        yield b"chunk"

    with pytest.raises(httpx.TransportError):
        sync_get(transport, target.url, method="POST", content=chunks())

    assert http_proxy.requests == []


#
# Regression tests: what is and is not the proxy's fault
#


@pytest.mark.parametrize("transport_class, get", CASES)
class TestProxyFaultClassification:
    def test_post_is_not_resent_when_the_proxy_drops_after_relaying(
        self, transport_class, get, make_http_proxy, target
    ):
        flaky = make_http_proxy(behaviour="drop_after_relay")
        good = make_http_proxy()
        transport = transport_class(ProxyList([flaky.proxy(), good.proxy()]))

        with pytest.raises(httpx.TransportError):
            get(transport, target.url, method="POST", content=b"charge=100")

        assert target.hits == [("POST", "/")]
        assert good.requests == []

    def test_wrong_credentials_are_a_failed_proxy_by_default(
        self, transport_class, get, make_http_proxy, target
    ):
        bad, good = make_http_proxy(), make_http_proxy()
        transport = transport_class(
            ProxyList([bad.proxy(password="wrong"), good.proxy()])
        )

        assert get(transport, target.url).content == BODY
        assert transport.provider.available_proxies() == [good.proxy()]

    def test_bad_url_does_not_blame_the_proxy(self, transport_class, get, http_proxy):
        transport = transport_class(ProxyList([http_proxy.proxy()]))

        with pytest.raises(httpx.UnsupportedProtocol):
            get(transport, "ftp://example.invalid/file")

        assert len(transport.provider.available_proxies()) == 1


def test_multipart_upload_is_not_retried(http_proxy, target):
    transport = RotatingTransport(ProxyList([dead_proxy(), http_proxy.proxy()]))

    with pytest.raises(httpx.TransportError):
        sync_get(
            transport, target.url, method="POST", files={"f": ("a.txt", b"PAYLOAD")}
        )

    assert http_proxy.requests == []
