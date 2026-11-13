"""report_failure / report_success: opt-in feedback that get_proxy() acts on."""

from datetime import timedelta

import pytest

from proxyproviders import Proxy, ProxyConfig, ProxyList, ProxyProvider
from proxyproviders.algorithms import First, Random


@pytest.fixture
def provider():
    return ProxyList(
        ["203.0.113.1:8080:u:p", "203.0.113.2:8080:u:p", "203.0.113.3:8080:u:p"]
    )


def addresses(proxies):
    return [p.proxy_address for p in proxies]


def expire_cooldowns(provider):
    provider._cooldowns = {
        key: until - timedelta(seconds=provider.config.failure_cooldown + 1)
        for key, until in provider._cooldowns.items()
    }


def test_nothing_changes_until_a_failure_is_reported(provider):
    assert provider.available_proxies() == provider.list_proxies()
    assert addresses(provider.get_proxy() for _ in range(4)) == [
        "203.0.113.1",
        "203.0.113.2",
        "203.0.113.3",
        "203.0.113.1",
    ]


def test_failed_proxy_is_skipped_by_every_algorithm(provider):
    first, second, third = provider.list_proxies()
    provider.report_failure(first)

    assert provider.available_proxies() == [second, third]
    assert provider.get_proxy(First()) is second
    assert {provider.get_proxy(Random()).proxy_address for _ in range(30)} == {
        "203.0.113.2",
        "203.0.113.3",
    }
    picked = {provider.get_proxy().proxy_address for _ in range(6)}
    assert picked == {"203.0.113.2", "203.0.113.3"}


def test_failed_proxy_stays_in_list_proxies(provider):
    provider.report_failure(provider.list_proxies()[0])
    assert len(provider.list_proxies()) == 3


def test_proxy_returns_after_the_cooldown(provider):
    first = provider.list_proxies()[0]
    provider.report_failure(first)
    assert first not in provider.available_proxies()

    expire_cooldowns(provider)
    assert first in provider.available_proxies()
    assert provider._cooldowns == {}


def test_report_success_brings_a_proxy_back_immediately(provider):
    first = provider.list_proxies()[0]
    provider.report_failure(first)
    provider.report_success(first)
    assert provider.get_proxy(First()) is first

    provider.report_success(first)  # reporting success with no failure is harmless


def test_all_failed_still_returns_a_proxy(provider):
    for proxy in provider.list_proxies():
        provider.report_failure(proxy)

    assert provider.available_proxies() == []
    assert provider.get_proxy() in provider.list_proxies()


def test_cooldown_comes_from_config_or_the_call():
    provider = ProxyList(
        ["203.0.113.1:8080", "203.0.113.2:8080"],
        config=ProxyConfig(failure_cooldown=1000),
    )
    first, second = provider.list_proxies()

    provider.report_failure(first)
    provider.report_failure(second, cooldown=0)

    assert provider.available_proxies() == [second]
    assert ProxyConfig().failure_cooldown == 60


def test_failure_survives_a_refresh():
    """Refreshing builds new Proxy objects, so health is not tied to object identity."""

    class Rebuilding(ProxyProvider):
        def _fetch_proxies(self):
            return [Proxy.from_string(f"203.0.113.{n}:8080:u:p") for n in range(1, 4)]

    provider = Rebuilding()
    before = provider.list_proxies()
    provider.report_failure(before[0])

    refreshed = provider.list_proxies(force_refresh=True)

    assert refreshed[0] is not before[0]
    assert addresses(provider.available_proxies()) == ["203.0.113.2", "203.0.113.3"]


def test_same_gateway_with_different_usernames_is_tracked_separately():
    provider = ProxyList(
        [
            "http://user-session-a:p@gate.example.com:8080",
            "http://user-session-b:p@gate.example.com:8080",
        ]
    )
    session_a, session_b = provider.list_proxies()
    provider.report_failure(session_a)
    assert provider.available_proxies() == [session_b]
