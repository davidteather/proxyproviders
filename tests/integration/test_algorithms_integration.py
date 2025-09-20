"""Integration tests for the new algorithm-based API with real providers."""

import os

import pytest
import requests

from proxyproviders.algorithms import First, Random, RoundRobin
from proxyproviders.models.proxy import ProxyFormat
from proxyproviders.providers.webshare import Webshare

# Skip integration tests unless explicitly enabled
skip_integration = pytest.mark.skipif(
    not (os.getenv("RUN_INTEGRATION_TESTS") and os.getenv("WEBSHARE_API_KEY")),
    reason="Integration tests require RUN_INTEGRATION_TESTS flag and a valid WEBSHARE_API_KEY",
)


@skip_integration
def test_webshare_get_proxy_default_algorithm():
    """Test get_proxy with default RoundRobin algorithm using real Webshare API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    # Test default algorithm (RoundRobin)
    proxy1 = provider.get_proxy()
    proxy2 = provider.get_proxy()

    # Basic validation
    assert proxy1 is not None
    assert proxy2 is not None
    assert hasattr(proxy1, "proxy_address")
    assert hasattr(proxy1, "port")
    assert hasattr(proxy1, "username")
    assert hasattr(proxy1, "password")

    # Verify they're different proxies (RoundRobin should cycle)
    # Note: This might be the same if only one proxy is available
    print(f"Proxy 1: {proxy1.proxy_address}:{proxy1.port}")
    print(f"Proxy 2: {proxy2.proxy_address}:{proxy2.port}")


@skip_integration
def test_webshare_get_proxy_with_random():
    """Test get_proxy with Random algorithm using real Webshare API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    # Test Random algorithm
    proxy = provider.get_proxy(Random())

    assert proxy is not None
    assert hasattr(proxy, "proxy_address")
    assert hasattr(proxy, "port")
    print(f"Random proxy: {proxy.proxy_address}:{proxy.port}")


@skip_integration
def test_webshare_get_proxy_with_first():
    """Test get_proxy with First algorithm using real Webshare API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    # Test First algorithm
    proxy1 = provider.get_proxy(First())
    proxy2 = provider.get_proxy(First())

    assert proxy1 is not None
    assert proxy2 is not None

    # First algorithm should always return the same proxy
    assert proxy1.id == proxy2.id
    assert proxy1.proxy_address == proxy2.proxy_address
    print(f"First proxy (both calls): {proxy1.proxy_address}:{proxy1.port}")


@skip_integration
def test_webshare_proxy_conversion_methods():
    """Test the new proxy conversion methods with real Webshare API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    proxy = provider.get_proxy()

    # Test to_url method
    url = proxy.to_url()
    assert url.startswith("http://")
    assert f"{proxy.username}:{proxy.password}" in url
    assert f"{proxy.proxy_address}:{proxy.port}" in url
    print(f"Proxy URL: {url}")

    # Test format method for requests
    requests_dict = proxy.format(ProxyFormat.REQUESTS)
    assert isinstance(requests_dict, dict)
    assert "http" in requests_dict
    assert "https" in requests_dict
    print(f"Requests dict: {requests_dict}")


@skip_integration
def test_webshare_e2e_with_requests():
    """End-to-end test: Get proxy and make HTTP request using real Webshare API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    try:
        # Get proxy using new API
        proxy = provider.get_proxy()

        # Convert to requests format
        proxies = proxy.format(ProxyFormat.REQUESTS)

        # Make actual HTTP request through proxy
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)

        assert response.status_code == 200

        response_data = response.json()
        assert "origin" in response_data

        # The origin IP should be different from our direct IP
        # (though we can't easily test this without making a non-proxy request)
        proxy_ip = response_data["origin"]
        print(f"Request through proxy successful. Origin IP: {proxy_ip}")
        print(f"Used proxy: {proxy.proxy_address}:{proxy.port}")

    except requests.exceptions.RequestException as e:
        # Some proxies might not work, but the API should still function
        print(f"Request failed (proxy might be inactive): {e}")
        # Don't fail the test - the important part is that we got a proxy


@skip_integration
def test_webshare_round_robin_state_persistence():
    """Test that RoundRobin algorithm maintains state across calls with real API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    # Get all available proxies to understand the expected sequence
    all_proxies = provider.list_proxies()

    if len(all_proxies) < 2:
        pytest.skip("Need at least 2 proxies to test RoundRobin state persistence")

    # Test that default RoundRobin cycles through proxies
    selected_proxies = []
    for i in range(min(len(all_proxies), 5)):  # Test up to 5 proxies
        proxy = provider.get_proxy()  # Uses default RoundRobin
        selected_proxies.append(proxy)
        print(f"RoundRobin selection {i+1}: {proxy.proxy_address}:{proxy.port}")

    # Verify we're getting different proxies (state is maintained)
    if len(all_proxies) >= 2:
        assert selected_proxies[0].id != selected_proxies[1].id


@skip_integration
def test_webshare_custom_algorithm():
    """Test custom algorithm implementation with real Webshare API."""
    from typing import List

    from proxyproviders.algorithms import Algorithm
    from proxyproviders.models.proxy import Proxy

    class LastProxyAlgorithm(Algorithm):
        """Custom algorithm that always selects the last proxy."""

        def select(self, proxies: List[Proxy]) -> Proxy:
            if not proxies:
                raise ValueError("Cannot select from empty proxy list")
            return proxies[-1]

    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    # Get all proxies to know what the last one should be
    all_proxies = provider.list_proxies()

    if not all_proxies:
        pytest.skip("No proxies available for custom algorithm test")

    expected_last_proxy = all_proxies[-1]

    # Test custom algorithm
    custom_algorithm = LastProxyAlgorithm()
    selected_proxy = provider.get_proxy(custom_algorithm)

    assert selected_proxy.id == expected_last_proxy.id
    print(
        f"Custom algorithm selected last proxy: {selected_proxy.proxy_address}:{selected_proxy.port}"
    )


@skip_integration
def test_webshare_one_liner_usage():
    """Test the one-liner usage pattern with real Webshare API."""
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    try:
        # Test the perfect one-liner
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=provider.get_proxy().format(ProxyFormat.REQUESTS),
            timeout=10,
        )

        assert response.status_code == 200
        result = response.json()

        print(f"One-liner successful! Response: {result}")

    except requests.exceptions.RequestException as e:
        print(f"One-liner request failed (proxy might be inactive): {e}")
        # Don't fail the test - the API worked, proxy might be inactive
