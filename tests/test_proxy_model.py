"""Tests for the Proxy model conversion methods."""

from datetime import datetime

import pytest

from proxyproviders.models.proxy import Proxy, ProxyFormat


@pytest.fixture
def sample_proxy():
    """Sample proxy for testing."""
    return Proxy(
        id="test-proxy-1",
        username="testuser",
        password="testpass",
        proxy_address="192.168.1.100",
        port=8080,
        country_code="US",
        city_name="New York",
        protocols=["http", "https"],
    )


@pytest.fixture
def sample_proxy_no_protocols():
    """Sample proxy without protocols specified."""
    return Proxy(
        id="test-proxy-2",
        username="user2",
        password="pass2",
        proxy_address="10.0.0.1",
        port=3128,
    )


class TestProxyToUrl:
    """Tests for Proxy.to_url() method."""

    def test_to_url_default_protocol(self, sample_proxy):
        """Test to_url with default http protocol."""
        url = sample_proxy.to_url()
        expected = "http://testuser:testpass@192.168.1.100:8080"
        assert url == expected

    def test_to_url_custom_protocol(self, sample_proxy):
        """Test to_url with custom protocol."""
        url = sample_proxy.to_url("https")
        expected = "https://testuser:testpass@192.168.1.100:8080"
        assert url == expected

    def test_to_url_socks_protocol(self, sample_proxy):
        """Test to_url with socks protocol."""
        url = sample_proxy.to_url("socks5")
        expected = "socks5://testuser:testpass@192.168.1.100:8080"
        assert url == expected

    def test_to_url_special_characters_in_credentials(self):
        """Test to_url with special characters in username/password."""
        proxy = Proxy(
            id="special",
            username="user@domain.com",
            password="pass:word!",
            proxy_address="192.168.1.1",
            port=8080,
        )
        url = proxy.to_url()
        expected = "http://user@domain.com:pass:word!@192.168.1.1:8080"
        assert url == expected


class TestProxyFormat:
    """Tests for Proxy.format() method."""

    def test_format_default_url(self, sample_proxy):
        """Test format with default URL format."""
        result = sample_proxy.format()
        expected = "http://testuser:testpass@192.168.1.100:8080"
        assert result == expected

    def test_format_url_with_protocol(self, sample_proxy):
        """Test format URL with custom protocol."""
        result = sample_proxy.format(ProxyFormat.URL, protocol="https")
        expected = "https://testuser:testpass@192.168.1.100:8080"
        assert result == expected

    def test_format_requests_default_protocols(self, sample_proxy):
        """Test format for requests with default protocols."""
        result = sample_proxy.format(ProxyFormat.REQUESTS)
        expected = {
            "http": "http://testuser:testpass@192.168.1.100:8080",
            "https": "http://testuser:testpass@192.168.1.100:8080",
        }
        assert result == expected

    def test_format_requests_no_protocols_specified(self, sample_proxy_no_protocols):
        """Test format for requests when proxy has no protocols specified."""
        result = sample_proxy_no_protocols.format(ProxyFormat.REQUESTS)
        expected = {
            "http": "http://user2:pass2@10.0.0.1:3128",
            "https": "http://user2:pass2@10.0.0.1:3128",
        }
        assert result == expected

    def test_format_requests_custom_protocols(self, sample_proxy):
        """Test format for requests with custom protocol list."""
        result = sample_proxy.format(ProxyFormat.REQUESTS, protocols=["http"])
        expected = {"http": "http://testuser:testpass@192.168.1.100:8080"}
        assert result == expected

    def test_format_requests_multiple_custom_protocols(self, sample_proxy):
        """Test format for requests with multiple custom protocols."""
        result = sample_proxy.format(
            ProxyFormat.REQUESTS, protocols=["http", "https", "ftp"]
        )
        expected = {
            "http": "http://testuser:testpass@192.168.1.100:8080",
            "https": "http://testuser:testpass@192.168.1.100:8080",
            "ftp": "http://testuser:testpass@192.168.1.100:8080",
        }
        assert result == expected

    def test_format_curl(self, sample_proxy):
        """Test format for curl."""
        result = sample_proxy.format(ProxyFormat.CURL)
        expected = ["-x", "http://testuser:testpass@192.168.1.100:8080"]
        assert result == expected

    def test_format_httpx(self, sample_proxy):
        """Test format for httpx."""
        result = sample_proxy.format(ProxyFormat.HTTPX)
        expected = {
            "http://": "http://testuser:testpass@192.168.1.100:8080",
            "https://": "http://testuser:testpass@192.168.1.100:8080",
        }
        assert result == expected

    def test_format_aiohttp(self, sample_proxy):
        """Test format for aiohttp."""
        result = sample_proxy.format(ProxyFormat.AIOHTTP)
        expected = "http://testuser:testpass@192.168.1.100:8080"
        assert result == expected

    def test_format_string_enum(self, sample_proxy):
        """Test format with string instead of enum."""
        result = sample_proxy.format("requests")
        expected = {
            "http": "http://testuser:testpass@192.168.1.100:8080",
            "https": "http://testuser:testpass@192.168.1.100:8080",
        }
        assert result == expected

    def test_format_unsupported_format(self, sample_proxy):
        """Test format with unsupported format type."""
        with pytest.raises(ValueError, match="is not a valid ProxyFormat"):
            sample_proxy.format("unsupported")

    def test_format_proxy_with_limited_protocols(self):
        """Test format with proxy that only supports specific protocols."""
        proxy = Proxy(
            id="limited",
            username="user",
            password="pass",
            proxy_address="192.168.1.1",
            port=8080,
            protocols=["http"],  # Only supports HTTP
        )

        # Should use proxy's own protocols when none specified
        result = proxy.format(ProxyFormat.REQUESTS)
        expected = {"http": "http://user:pass@192.168.1.1:8080"}
        assert result == expected

        # Should respect custom protocols even if proxy doesn't list them
        result = proxy.format(ProxyFormat.REQUESTS, protocols=["https"])
        expected = {"https": "http://user:pass@192.168.1.1:8080"}
        assert result == expected


class TestProxyIntegration:
    """Integration tests for Proxy methods."""

    def test_format_and_to_url_consistency(self, sample_proxy):
        """Test that format and to_url methods are consistent."""
        url_result = sample_proxy.to_url("http")
        format_result = sample_proxy.format(ProxyFormat.URL, protocol="http")

        assert url_result == format_result

        # Test requests format consistency
        requests_result = sample_proxy.format(ProxyFormat.REQUESTS, protocols=["http"])
        assert requests_result["http"] == url_result

    def test_proxy_with_all_fields(self):
        """Test proxy conversion with all optional fields populated."""
        proxy = Proxy(
            id="full-proxy",
            username="fulluser",
            password="fullpass",
            proxy_address="example.com",
            port=8080,
            country_code="US",
            city_name="San Francisco",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            protocols=["http", "https", "socks5"],
        )

        url = proxy.format(ProxyFormat.URL)
        assert url == "http://fulluser:fullpass@example.com:8080"

        requests_dict = proxy.format(ProxyFormat.REQUESTS)
        expected = {
            "http": "http://fulluser:fullpass@example.com:8080",
            "https": "http://fulluser:fullpass@example.com:8080",
            "socks5": "http://fulluser:fullpass@example.com:8080",
        }
        assert requests_dict == expected

    def test_all_format_types_work(self, sample_proxy):
        """Test that all format types return expected types."""
        # URL format returns string
        url_result = sample_proxy.format(ProxyFormat.URL)
        assert isinstance(url_result, str)

        # REQUESTS format returns dict
        requests_result = sample_proxy.format(ProxyFormat.REQUESTS)
        assert isinstance(requests_result, dict)

        # CURL format returns list
        curl_result = sample_proxy.format(ProxyFormat.CURL)
        assert isinstance(curl_result, list)

        # HTTPX format returns dict
        httpx_result = sample_proxy.format(ProxyFormat.HTTPX)
        assert isinstance(httpx_result, dict)

        # AIOHTTP format returns string
        aiohttp_result = sample_proxy.format(ProxyFormat.AIOHTTP)
        assert isinstance(aiohttp_result, str)
