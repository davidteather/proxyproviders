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

    def test_format_playwright_with_auth(self, sample_proxy):
        """Test format for Playwright with authentication."""
        result = sample_proxy.format(ProxyFormat.PLAYWRIGHT)
        expected = {
            "server": "http://192.168.1.100:8080",
            "username": "testuser",
            "password": "testpass",
        }
        assert result == expected

    def test_format_playwright_without_auth(self, sample_proxy_no_protocols):
        """Test format for Playwright with authentication (sample_proxy_no_protocols has auth)."""
        result = sample_proxy_no_protocols.format(ProxyFormat.PLAYWRIGHT)
        expected = {
            "server": "http://10.0.0.1:3128",
            "username": "user2",
            "password": "pass2",
        }
        assert result == expected

    def test_format_playwright_empty_credentials(self):
        """Test format for Playwright with empty username/password."""
        proxy = Proxy(
            id="no-auth",
            username="",
            password="",
            proxy_address="192.168.1.1",
            port=8080,
        )
        result = proxy.format(ProxyFormat.PLAYWRIGHT)
        expected = {"server": "http://192.168.1.1:8080"}
        assert result == expected

    def test_format_playwright_none_credentials(self):
        """Test format for Playwright with None username/password."""
        proxy = Proxy(
            id="none-auth",
            username=None,
            password=None,
            proxy_address="192.168.1.1",
            port=8080,
        )
        result = proxy.format(ProxyFormat.PLAYWRIGHT)
        expected = {"server": "http://192.168.1.1:8080"}
        assert result == expected

    def test_format_playwright_string_format(self, sample_proxy):
        """Test format for Playwright using string format."""
        result = sample_proxy.format("playwright")
        expected = {
            "server": "http://192.168.1.100:8080",
            "username": "testuser",
            "password": "testpass",
        }
        assert result == expected

    def test_format_playwright_with_protocol(self, sample_proxy):
        """Test format for Playwright with specific protocol."""
        # Test with https protocol
        result = sample_proxy.format(ProxyFormat.PLAYWRIGHT, protocol="https")
        expected = {
            "server": "https://192.168.1.100:8080",
            "username": "testuser",
            "password": "testpass",
        }
        assert result == expected

    def test_format_playwright_with_socks5(self):
        """Test format for Playwright with SOCKS5 protocol."""
        # Create a proxy that supports SOCKS5
        proxy = Proxy(
            id="socks5-test",
            username="testuser",
            password="testpass",
            proxy_address="192.168.1.100",
            port=8080,
            protocols=["http", "https", "socks5"],  # Include socks5 support
        )

        result = proxy.format(ProxyFormat.PLAYWRIGHT, protocol="socks5")
        expected = {
            "server": "socks5://192.168.1.100:8080",
            "username": "testuser",
            "password": "testpass",
        }
        assert result == expected

    def test_format_playwright_protocol_fallback(self):
        """Test format for Playwright with protocol fallback."""
        # Create proxy with limited protocols
        proxy = Proxy(
            id="limited-protocol",
            username="user",
            password="pass",
            proxy_address="192.168.1.1",
            port=8080,
            protocols=["http"],  # Only supports HTTP
        )

        # Request unsupported protocol, should fallback to http
        result = proxy.format(ProxyFormat.PLAYWRIGHT, protocol="socks5")
        expected = {
            "server": "http://192.168.1.1:8080",
            "username": "user",
            "password": "pass",
        }
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
        with pytest.raises(ValueError, match="Invalid format type"):
            sample_proxy.format("unsupported")

    def test_format_invalid_type_not_string_or_enum(self, sample_proxy):
        """Test format with invalid type (not string or ProxyFormat enum)."""
        with pytest.raises(
            ValueError,
            match="Invalid format type: int. Expected ProxyFormat enum or string.",
        ):
            sample_proxy.format(123)  # int instead of string/enum

    def test_format_invalid_type_none(self, sample_proxy):
        """Test format with None type."""
        with pytest.raises(
            ValueError,
            match="Invalid format type: NoneType. Expected ProxyFormat enum or string.",
        ):
            sample_proxy.format(None)

    def test_format_invalid_type_list(self, sample_proxy):
        """Test format with list type."""
        with pytest.raises(
            ValueError,
            match="Invalid format type: list. Expected ProxyFormat enum or string.",
        ):
            sample_proxy.format(["requests"])

    def test_format_invalid_type_dict(self, sample_proxy):
        """Test format with dict type."""
        with pytest.raises(
            ValueError,
            match="Invalid format type: dict. Expected ProxyFormat enum or string.",
        ):
            sample_proxy.format({"format": "requests"})

    def test_format_handlers_complete_coverage(self, sample_proxy):
        """Test that all ProxyFormat enum values have corresponding handlers."""
        # This test ensures that if someone adds a new ProxyFormat enum value,
        # they must also add a corresponding handler in the format_handlers dictionary

        # Get all ProxyFormat enum values
        all_proxy_formats = set(ProxyFormat)

        # Test that each format can be processed without KeyError
        for format_type in all_proxy_formats:
            try:
                result = sample_proxy.format(format_type)
                assert (
                    result is not None
                ), f"Format {format_type.value} should return a result"
            except KeyError as e:
                pytest.fail(f"Missing handler for ProxyFormat.{format_type.name}: {e}")
            except Exception as e:
                # Other exceptions are fine (like validation errors), but KeyError means missing handler
                if "KeyError" in str(type(e)):
                    pytest.fail(
                        f"Missing handler for ProxyFormat.{format_type.name}: {e}"
                    )

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

        # PLAYWRIGHT format returns dict
        playwright_result = sample_proxy.format(ProxyFormat.PLAYWRIGHT)
        assert isinstance(playwright_result, dict)
