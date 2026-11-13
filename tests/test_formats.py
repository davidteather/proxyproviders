"""Tests for the output formats added alongside the originals, and for parsing text."""

import pytest

from proxyproviders import Proxy, ProxyFormat


@pytest.fixture
def proxy():
    return Proxy(
        id="p1",
        username="user",
        password="pass",
        proxy_address="proxy.example.com",
        port=8080,
        protocols=["http", "https"],
    )


@pytest.fixture
def socks_proxy(proxy):
    proxy.port = 1080
    proxy.protocols = ["socks5"]
    return proxy


URL = "http://user:pass@proxy.example.com:8080"
SOCKS_URL = "socks5://user:pass@proxy.example.com:1080"


class TestNewFormats:
    def test_every_format_has_a_formatter(self, proxy):
        for format_type in ProxyFormat:
            assert proxy.format(format_type)
            assert proxy.format(format_type.value) == proxy.format(format_type)

    def test_httpx_is_the_url_for_the_proxy_argument(self, proxy):
        assert proxy.format(ProxyFormat.HTTPX) == URL

    def test_scrapy(self, proxy):
        assert proxy.format(ProxyFormat.SCRAPY) == URL

    def test_urllib_matches_requests(self, proxy):
        assert proxy.format(ProxyFormat.URLLIB) == {"http": URL, "https": URL}
        assert proxy.format(ProxyFormat.URLLIB) == proxy.format(ProxyFormat.REQUESTS)

    def test_env(self, proxy):
        assert proxy.format(ProxyFormat.ENV) == {
            "HTTP_PROXY": URL,
            "http_proxy": URL,
            "HTTPS_PROXY": URL,
            "https_proxy": URL,
        }

    def test_env_for_socks_adds_all_proxy(self, socks_proxy):
        env = socks_proxy.format(ProxyFormat.ENV)
        assert env["ALL_PROXY"] == env["all_proxy"] == SOCKS_URL
        assert env["HTTPS_PROXY"] == SOCKS_URL

    def test_host_port_user_pass(self, proxy):
        assert proxy.format(ProxyFormat.HOST_PORT_USER_PASS) == (
            "proxy.example.com:8080:user:pass"
        )

    def test_host_port_without_credentials(self, proxy):
        proxy.username = proxy.password = ""
        assert proxy.format(ProxyFormat.HOST_PORT_USER_PASS) == "proxy.example.com:8080"


class TestNoCredentials:
    """A proxy that needs no login must not get an empty ':@' in its URL."""

    def test_to_url(self, proxy):
        proxy.username = proxy.password = ""
        assert proxy.to_url() == "http://proxy.example.com:8080"
        assert proxy.format(ProxyFormat.REQUESTS)["https"] == (
            "http://proxy.example.com:8080"
        )

    def test_playwright_omits_credentials(self, proxy):
        proxy.username = proxy.password = ""
        assert proxy.format(ProxyFormat.PLAYWRIGHT) == {
            "server": "http://proxy.example.com:8080"
        }


class TestFromString:
    @pytest.mark.parametrize(
        "text",
        [
            "http://user:pass@proxy.example.com:8080",
            "user:pass@proxy.example.com:8080",
            "proxy.example.com:8080:user:pass",
            "  proxy.example.com:8080:user:pass\n",
        ],
    )
    def test_accepted_forms(self, text):
        proxy = Proxy.from_string(text)
        assert proxy.to_url() == URL
        assert proxy.id == "proxy.example.com:8080"
        assert proxy.protocols == ["http", "https"]

    def test_host_and_port_only(self):
        proxy = Proxy.from_string("203.0.113.7:3128")
        assert (proxy.username, proxy.password) == ("", "")
        assert proxy.to_url() == "http://203.0.113.7:3128"

    def test_socks_url(self):
        proxy = Proxy.from_url(SOCKS_URL)
        assert proxy.protocols == ["socks5"]
        assert proxy.to_url() == SOCKS_URL

    def test_password_may_contain_colons(self):
        proxy = Proxy.from_string("proxy.example.com:8080:user:pa:ss:word")
        assert proxy.password == "pa:ss:word"

    @pytest.mark.parametrize("password", ["p#ss", "pa/ss", "p?ss", "p@ss", "p%41ss"])
    def test_round_trips_through_to_url(self, password):
        original = Proxy(
            id="x",
            username="user-country-us",
            password=password,
            proxy_address="proxy.example.com",
            port=8080,
        )
        parsed = Proxy.from_url(original.to_url())
        assert (parsed.username, parsed.password) == ("user-country-us", password)
        assert parsed.to_url() == original.to_url()

    def test_round_trips_through_host_port_user_pass(self, proxy):
        line = proxy.format(ProxyFormat.HOST_PORT_USER_PASS)
        assert Proxy.from_string(line).to_url() == proxy.to_url()

    def test_id_and_extra_fields(self):
        proxy = Proxy.from_string(URL, id="mine", country_code="US")
        assert proxy.id == "mine"
        assert proxy.country_code == "US"

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "proxy.example.com",
            "proxy.example.com:notaport",
            "proxy.example.com:99999",
            "proxy.example.com:8080:useronly",
            "http://proxy.example.com",
            "http://user:pass@proxy.example.com:notaport",
            "ftp://proxy.example.com:21",
            "https://user:pass@proxy.example.com:8080",
            ":8080",
        ],
    )
    def test_rejects_what_it_cannot_parse(self, text):
        with pytest.raises(ValueError):
            Proxy.from_string(text)

    def test_error_does_not_guess_at_https(self):
        with pytest.raises(ValueError, match="TLS to the proxy"):
            Proxy.from_url("https://proxy.example.com:8080")


class TestParsingEdgeCases:
    """Cases the first version of the parser got wrong."""

    def test_at_sign_in_a_colon_form_password(self):
        proxy = Proxy.from_string("1.2.3.4:8080:user:p@ss")
        assert (proxy.proxy_address, proxy.port) == ("1.2.3.4", 8080)
        assert (proxy.username, proxy.password) == ("user", "p@ss")

    def test_colon_form_is_never_reinterpreted_as_another_host(self):
        """An '@host:port' inside the password must not become the proxy address."""
        proxy = Proxy.from_string("1.2.3.4:8080:user:x@evil.example:9000")
        assert (proxy.proxy_address, proxy.port) == ("1.2.3.4", 8080)
        assert proxy.password == "x@evil.example:9000"

    @pytest.mark.parametrize("password", ["p@ss", "a:b@c", "p#ss/w?rd", "pä55"])
    def test_host_port_user_pass_round_trips(self, proxy, password):
        proxy.password = password
        line = proxy.format(ProxyFormat.HOST_PORT_USER_PASS)
        parsed = Proxy.from_string(line)
        assert parsed.password == password
        assert parsed.to_url() == proxy.to_url()

    def test_user_pass_at_host_port_still_parses(self):
        proxy = Proxy.from_string("user:pass@proxy.example.com:8080")
        assert proxy.to_url() == URL

    @pytest.mark.parametrize(
        "text",
        [
            "http://proxy.example.com:0",
            "proxy.example.com:0",
            "h :8080",
            "http://proxy.example.com:8080/path",
            "http://proxy.example.com:8080?x=1",
        ],
    )
    def test_rejects_malformed_addresses(self, text):
        with pytest.raises(ValueError):
            Proxy.from_string(text)

    def test_trailing_slash_is_allowed(self):
        assert Proxy.from_url("http://proxy.example.com:8080/").port == 8080


class TestIPv6:
    def test_url_round_trip(self):
        proxy = Proxy.from_url("http://user:pass@[2001:db8::1]:8080")
        assert proxy.proxy_address == "2001:db8::1"
        assert proxy.to_url() == "http://user:pass@[2001:db8::1]:8080"
        assert Proxy.from_url(proxy.to_url()).proxy_address == "2001:db8::1"

    def test_host_port_user_pass_round_trip(self):
        proxy = Proxy.from_string("[2001:db8::1]:8080:user:pass")
        assert (proxy.proxy_address, proxy.port) == ("2001:db8::1", 8080)
        line = proxy.format(ProxyFormat.HOST_PORT_USER_PASS)
        assert line == "[2001:db8::1]:8080:user:pass"
        assert Proxy.from_string(line).to_url() == proxy.to_url()

    def test_playwright_server(self):
        proxy = Proxy.from_string("[::1]:8080")
        assert proxy.format(ProxyFormat.PLAYWRIGHT) == {"server": "http://[::1]:8080"}

    def test_unbracketed_ipv6_is_rejected(self):
        with pytest.raises(ValueError):
            Proxy.from_string("2001:db8::1:8080")
