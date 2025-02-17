import pytest
from proxyproviders.proxy_provider import ProxyProvider, ProxyConfig
from datetime import timedelta
from typing import List
from proxyproviders.models.proxy import Proxy

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
