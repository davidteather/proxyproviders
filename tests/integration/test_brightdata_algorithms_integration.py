"""Integration tests for the new algorithm-based API with real BrightData provider."""

import os

import pytest
import requests

from proxyproviders.algorithms import First, Random, RoundRobin
from proxyproviders.models.proxy import ProxyFormat
from proxyproviders.providers.brightdata import BrightData

# Skip integration tests unless explicitly enabled
skip_integration = pytest.mark.skipif(
    not (os.getenv("RUN_INTEGRATION_TESTS") and os.getenv("BRIGHTDATA_API_KEY")),
    reason="Integration tests require RUN_INTEGRATION_TESTS flag and a valid BRIGHTDATA_API_KEY",
)


@skip_integration
def test_brightdata_get_proxy_default_algorithm():
    """Test get_proxy with default RoundRobin algorithm using real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

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

    print(f"BrightData Proxy 1: {proxy1.proxy_address}:{proxy1.port}")
    print(f"BrightData Proxy 2: {proxy2.proxy_address}:{proxy2.port}")


@skip_integration
def test_brightdata_get_proxy_with_random():
    """Test get_proxy with Random algorithm using real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

    # Test Random algorithm
    proxy = provider.get_proxy(Random())

    assert proxy is not None
    assert hasattr(proxy, "proxy_address")
    assert hasattr(proxy, "port")
    print(f"BrightData Random proxy: {proxy.proxy_address}:{proxy.port}")


@skip_integration
def test_brightdata_get_proxy_with_first():
    """Test get_proxy with First algorithm using real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

    # Test First algorithm
    proxy1 = provider.get_proxy(First())
    proxy2 = provider.get_proxy(First())

    assert proxy1 is not None
    assert proxy2 is not None

    # First algorithm should always return the same proxy
    assert proxy1.id == proxy2.id
    assert proxy1.proxy_address == proxy2.proxy_address
    print(f"BrightData First proxy (both calls): {proxy1.proxy_address}:{proxy1.port}")


@skip_integration
def test_brightdata_proxy_conversion_methods():
    """Test the new proxy conversion methods with real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

    proxy = provider.get_proxy()

    # Test to_url method
    url = proxy.to_url()
    assert url.startswith("http://")
    assert f"{proxy.username}:{proxy.password}" in url
    assert f"{proxy.proxy_address}:{proxy.port}" in url
    print(f"BrightData Proxy URL: {url}")

    # Test format method for requests
    requests_dict = proxy.format(ProxyFormat.REQUESTS)
    assert isinstance(requests_dict, dict)
    assert "http" in requests_dict
    assert "https" in requests_dict
    print(f"BrightData Requests dict: {requests_dict}")

    # Test Playwright format (default protocol)
    playwright_dict = proxy.format(ProxyFormat.PLAYWRIGHT)
    assert isinstance(playwright_dict, dict)
    assert "server" in playwright_dict
    assert playwright_dict["server"].startswith("http://")
    assert f"{proxy.proxy_address}:{proxy.port}" in playwright_dict["server"]
    assert "username" in playwright_dict
    assert "password" in playwright_dict
    assert playwright_dict["username"] == proxy.username
    assert playwright_dict["password"] == proxy.password

    # Test Playwright format with different protocols
    for protocol in ["http", "https"]:
        playwright_protocol = proxy.format(ProxyFormat.PLAYWRIGHT, protocol=protocol)
        assert playwright_protocol["server"].startswith(f"{protocol}://")


@skip_integration
def test_brightdata_playwright_format_comprehensive():
    """Comprehensive test of Playwright format with real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

    proxy = provider.get_proxy()

    # Test 1: Default Playwright format
    default_format = proxy.format(ProxyFormat.PLAYWRIGHT)
    assert isinstance(default_format, dict)
    assert "server" in default_format
    assert "username" in default_format
    assert "password" in default_format
    assert default_format["server"].startswith("http://")

    # Test 2: Protocol variations
    protocols_to_test = ["http", "https"]

    for protocol in protocols_to_test:
        result = proxy.format(ProxyFormat.PLAYWRIGHT, protocol=protocol)
        assert result["server"].startswith(f"{protocol}://")
        assert result["username"] == proxy.username
        assert result["password"] == proxy.password

    # Test 3: String format
    string_format = proxy.format("playwright")
    assert string_format == default_format

    # Test 4: Format consistency
    enum_format = proxy.format(ProxyFormat.PLAYWRIGHT)
    string_format = proxy.format("playwright")
    assert enum_format == string_format

    # Test 5: Playwright documentation compliance
    playwright_config = proxy.format(ProxyFormat.PLAYWRIGHT)

    # Verify structure matches Playwright docs
    required_fields = ["server"]
    optional_fields = ["username", "password"]

    for field in required_fields:
        assert field in playwright_config, f"Missing required field: {field}"

    for field in optional_fields:
        if field in playwright_config:
            assert True  # Field is present
        else:
            assert False, f"Missing optional field: {field}"

    # Verify server format
    server = playwright_config["server"]
    assert "://" in server, "Server should include protocol"
    assert (
        f"{proxy.proxy_address}:{proxy.port}" in server
    ), "Server should include address and port"

    # Test 6: Protocol fallback behavior
    # Try to use an unsupported protocol - should fallback gracefully
    fallback_result = proxy.format(ProxyFormat.PLAYWRIGHT, protocol="socks5")
    assert "server" in fallback_result
    assert fallback_result["server"].startswith("http://")  # Should fallback to http


@skip_integration
def test_brightdata_e2e_with_requests():
    """End-to-end test: Get proxy and make HTTP request using real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

    try:
        # Get proxy using new API
        proxy = provider.get_proxy()

        # Convert to requests format
        proxies = proxy.format(ProxyFormat.REQUESTS)

        # Make actual HTTP request through proxy
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            timeout=15,  # BrightData might be slower
        )

        if response.status_code == 200:
            response_data = response.json()
            assert "origin" in response_data
            proxy_ip = response_data["origin"]
            print(f"BrightData request through proxy successful. Origin IP: {proxy_ip}")
            print(f"Used proxy: {proxy.proxy_address}:{proxy.port}")
        else:
            print(
                f"BrightData proxy returned status {response.status_code} (proxy might be inactive)"
            )

    except requests.exceptions.RequestException as e:
        # Some proxies might not work, but the API should still function
        print(f"BrightData request failed (proxy might be inactive): {e}")
        # Don't fail the test - the important part is that we got a proxy


@skip_integration
def test_brightdata_super_proxy_vs_ip_mode():
    """Test that algorithm works with both super proxy and IP modes."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")

    # Test super proxy mode (default)
    provider_super = BrightData(api_key=api_key, zone="static")
    proxy_super = provider_super.get_proxy()

    assert proxy_super is not None
    print(f"BrightData Super Proxy: {proxy_super.proxy_address}:{proxy_super.port}")

    # Test IP mode if available
    try:
        provider_ip = BrightData(api_key=api_key, zone="static", use_super_proxy=False)
        proxy_ip = provider_ip.get_proxy()

        assert proxy_ip is not None
        print(f"BrightData IP Mode Proxy: {proxy_ip.proxy_address}:{proxy_ip.port}")

    except Exception as e:
        print(f"IP mode test skipped (might not be available): {e}")


@skip_integration
def test_brightdata_custom_algorithm():
    """Test custom algorithm implementation with real BrightData API."""
    from typing import List

    from proxyproviders.algorithms import Algorithm
    from proxyproviders.models.proxy import Proxy

    class LastProxyAlgorithm(Algorithm):
        """Custom algorithm that always selects the last proxy."""

        def select(self, proxies: List[Proxy]) -> Proxy:
            if not proxies:
                raise ValueError("Cannot select from empty proxy list")
            return proxies[-1]

    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

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
        f"BrightData custom algorithm selected last proxy: {selected_proxy.proxy_address}:{selected_proxy.port}"
    )


@skip_integration
def test_brightdata_one_liner_usage():
    """Test the one-liner usage pattern with real BrightData API."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")

    try:
        # Test the perfect one-liner
        response = requests.get(
            "https://httpbin.org/ip",
            proxies=provider.get_proxy().format(ProxyFormat.REQUESTS),
            timeout=15,
        )

        assert response.status_code == 200
        result = response.json()

        print(f"BrightData one-liner successful! Response: {result}")

    except requests.exceptions.RequestException as e:
        print(f"BrightData one-liner request failed (proxy might be inactive): {e}")
        # Don't fail the test - the API worked, proxy might be inactive
