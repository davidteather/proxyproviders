import logging
import threading
import time
from datetime import timedelta
from typing import List

import pytest

from proxyproviders.models.proxy import Proxy
from proxyproviders.proxy_provider import ProxyConfig, ProxyProvider


class MockProxyProvider(ProxyProvider):
    """Mock implementation of ProxyProvider for testing."""

    def _fetch_proxies(self):
        return []


def test_should_refresh():
    """
    Test that the provider correctly determines whether it should refresh proxies.
    """
    provider = MockProxyProvider(config=ProxyConfig(refresh_interval=10))
    # Initially, no proxies exist so it should refresh.
    assert provider.should_refresh() is True
    # Simulate a fetch to set proxies and update the refresh timestamp.
    provider._set_proxies([])
    # Immediately afterward, it should not refresh because the interval has not passed.
    assert provider.should_refresh() is False


def test_list_proxies():
    """
    Test that list_proxies returns a list even if no proxies are available.
    """
    provider = MockProxyProvider()
    assert isinstance(provider.list_proxies(), list)


def test_force_refresh():
    """
    Test that list_proxies fetches new proxies when force_refresh is True.
    """

    # Directly subclassing the ProxyProvider for this test
    # for simplicity and to avoid the need for a real provider.
    class TestProxyProvider(MockProxyProvider):
        def _fetch_proxies(self) -> List[Proxy]:
            proxies = [1, 2, 3]
            return proxies

    provider = TestProxyProvider()

    print(provider._proxies)
    assert provider._proxies is None

    proxies = provider.list_proxies(force_refresh=True)
    print(proxies)

    assert proxies == [1, 2, 3]

    assert provider.list_proxies() == [1, 2, 3]


def test_refresh_interval():
    """
    Tests around the refresh_interval configuration.
    """

    # When refresh_interval is 0, it should never refresh automatically
    provider = MockProxyProvider(config=ProxyConfig(refresh_interval=0))
    provider._fetch_proxies = lambda: [1, 2, 3]

    # Simulate a fetch and set proxies to check refresh
    provider._set_proxies([1, 2, 3])
    assert provider.list_proxies() == [1, 2, 3]

    # Should not refresh since refresh_interval is 0
    assert provider.should_refresh() is False

    # Simulate a time lapse, but the proxies should not refresh
    provider._last_refresh = provider._last_refresh - timedelta(seconds=1)
    assert provider.should_refresh() is False

    # When refresh_interval is set to a value, refresh should happen after the specified interval
    provider = MockProxyProvider(config=ProxyConfig(refresh_interval=10))
    provider._fetch_proxies = lambda: [1, 2, 3]
    provider._set_proxies([1, 2, 3])
    assert provider.list_proxies() == [1, 2, 3]

    # Simulate the interval passing (10 seconds)
    provider._last_refresh = provider._last_refresh - timedelta(seconds=11)
    assert provider.should_refresh() is True

    # Fetch new proxies after interval has passed
    provider._set_proxies([4, 5, 6])
    assert provider.list_proxies() == [4, 5, 6]


#
# Concurrency and failed refreshes
#


class CountingProvider(ProxyProvider):
    """Counts fetches, and can be told to fail or to be slow."""

    def __init__(self, config=None, delay=0.0):
        super().__init__(config)
        self.calls = 0
        self.fail = False
        self.delay = delay

    def _fetch_proxies(self):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("provider is down")
        return [f"proxy-{self.calls}"]


def make_stale(provider):
    provider._last_refresh = provider._last_refresh - timedelta(
        seconds=provider.config.refresh_interval + 1
    )


def test_concurrent_callers_trigger_one_fetch():
    provider = CountingProvider(delay=0.05)
    results = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        results.append(provider.list_proxies())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert provider.calls == 1
    assert results == [["proxy-1"]] * 8


def test_concurrent_callers_trigger_one_refresh_when_stale():
    provider = CountingProvider(delay=0.05)
    provider.list_proxies()
    make_stale(provider)

    threads = [threading.Thread(target=provider.list_proxies) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert provider.calls == 2
    assert provider.list_proxies() == ["proxy-2"]


def test_failed_refresh_serves_previous_list(caplog):
    provider = CountingProvider()
    assert provider.list_proxies() == ["proxy-1"]

    provider.fail = True
    make_stale(provider)
    with caplog.at_level(logging.WARNING, logger="proxyproviders.proxy_provider"):
        assert provider.list_proxies() == ["proxy-1"]

    assert "serving the previous list" in caplog.text
    assert provider.calls == 2


def test_failed_refresh_is_not_retried_on_every_call():
    provider = CountingProvider()
    provider.list_proxies()
    provider.fail = True
    make_stale(provider)

    for _ in range(5):
        assert provider.list_proxies() == ["proxy-1"]
    assert provider.calls == 2  # the first fetch and one failed refresh

    # Once the retry delay has passed the provider is tried again, and recovers
    provider.fail = False
    provider._retry_refresh_after = provider._retry_refresh_after - timedelta(
        seconds=provider.config.refresh_retry_delay + 1
    )
    assert provider.list_proxies() == ["proxy-3"]
    assert provider._retry_refresh_after is None


def test_failed_first_fetch_raises():
    provider = CountingProvider()
    provider.fail = True
    with pytest.raises(RuntimeError):
        provider.list_proxies()


def test_failed_force_refresh_raises_and_keeps_previous_list():
    provider = CountingProvider()
    provider.list_proxies()
    provider.fail = True

    with pytest.raises(RuntimeError):
        provider.list_proxies(force_refresh=True)

    assert provider.list_proxies() == ["proxy-1"]


def test_config_defaults():
    config = ProxyConfig()
    assert config.timeout == 30
    assert config.refresh_retry_delay == 30
