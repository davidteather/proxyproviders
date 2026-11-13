"""Rotation, retries and failure reporting with proxies from any source."""

import requests

from proxyproviders import ProxyFormat, ProxyList, RotatingSession


def own_list_example():
    """Use proxies you already have, from a vendor without a built-in provider.

    The addresses below are documentation placeholders that do not exist. Replace
    them with real proxies before running this file.
    """
    provider = ProxyList(
        [
            "http://user:pass@203.0.113.7:8080",
            "203.0.113.8:8080:user:pass",
        ]
    )
    # Or: ProxyList.from_file("proxies.txt")
    return provider


def rotating_session_example(provider):
    """Let the session pick a proxy per request and retry on the next one."""
    session = RotatingSession(provider, max_retries=3, retry_statuses={403, 429})

    response = session.get("https://httpbin.org/ip", timeout=10)
    print(response.json(), "via", session.last_proxy)


def manual_failure_reporting_example(provider):
    """Do the requests yourself and tell the provider which proxies fail."""
    proxy = provider.get_proxy()
    try:
        requests.get(
            "https://httpbin.org/ip",
            proxies=proxy.format(ProxyFormat.REQUESTS),
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        # get_proxy() now skips this proxy for ProxyConfig.failure_cooldown seconds
        provider.report_failure(proxy)

    print("still in rotation:", provider.available_proxies())


def main():
    provider = own_list_example()
    rotating_session_example(provider)
    manual_failure_reporting_example(provider)


if __name__ == "__main__":
    main()
