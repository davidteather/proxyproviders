import pytest

from proxyproviders import NodeMaven, ProxyConfig


def provider(**kwargs):
    kwargs.setdefault("username", "user")
    kwargs.setdefault("password", "pass")
    return NodeMaven(**kwargs)


def test_default_is_one_sticky_session():
    proxies = provider().list_proxies()
    assert len(proxies) == 1
    proxy = proxies[0]
    assert proxy.proxy_address == "gate.nodemaven.com"
    assert proxy.port == 8080
    assert proxy.protocols == ["http", "https"]
    assert proxy.username == f"user-sid-{proxy.id}"
    assert proxy.password == "pass"


def test_sessions_get_distinct_hex_ids():
    proxies = provider(sessions=5).list_proxies()
    ids = [p.id for p in proxies]
    assert len(set(ids)) == 5
    for p in proxies:
        int(p.id, 16)  # hex, so no '-' inside the session id
        assert len(p.id) == 12


def test_targeting_and_ttl_go_into_the_username():
    proxy = provider(
        username_suffix="-country-us-region-california", ttl="30m"
    ).list_proxies()[0]
    assert proxy.username == f"user-country-us-region-california-sid-{proxy.id}-ttl-30m"


def test_zero_sessions_returns_one_rotating_proxy():
    proxies = provider(sessions=0, username_suffix="-country-de").list_proxies()
    assert len(proxies) == 1
    assert proxies[0].id == "rotating"
    assert proxies[0].username == "user-country-de"


def test_socks5_uses_its_own_port():
    proxy = provider(protocol="socks5").list_proxies()[0]
    assert proxy.port == 1080
    assert proxy.protocols == ["socks5"]


def test_refresh_draws_new_sessions():
    nm = provider(sessions=2, config=ProxyConfig(refresh_interval=0))
    first = [p.id for p in nm.list_proxies()]
    assert [p.id for p in nm.list_proxies()] == first  # cached, same exits
    assert [p.id for p in nm.list_proxies(force_refresh=True)] != first


@pytest.mark.parametrize(
    "kwargs",
    [
        {"username": ""},
        {"password": ""},
        {"sessions": -1},
        {"protocol": "socks4"},
        {"username_suffix": "-country-us-sid-abc"},
    ],
)
def test_invalid_arguments_are_refused(kwargs):
    with pytest.raises(ValueError):
        provider(**kwargs)
