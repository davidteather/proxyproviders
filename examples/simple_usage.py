"""Simple usage examples showing algorithm-based selection."""

import requests

from proxyproviders import Webshare
from proxyproviders.algorithms import First, Random, RoundRobin
from proxyproviders.models.proxy import ProxyFormat


def main():
    # Initialize provider
    provider = Webshare(api_key="your_api_key")

    # Default uses RoundRobin to cycle through proxies
    proxy = provider.get_proxy()
    requests.get("https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS))

    # Perfect for quick scripts
    requests.get(
        "https://httpbin.org/ip",
        proxies=provider.get_proxy().format(ProxyFormat.REQUESTS),
    )

    # Random proxy each time
    provider.get_proxy(Random())

    # Always first proxy
    provider.get_proxy(First())

    # Reusable RoundRobin instance
    round_robin = RoundRobin()
    provider.get_proxy(round_robin)
    provider.get_proxy(round_robin)  # Next proxy

    proxy = provider.get_proxy()

    # Default URL format
    proxy.format()  # "http://user:pass@host:port"

    # Requests format, for requests library
    proxy.format(ProxyFormat.REQUESTS)
    # {"http": "http://...", "https": "http://..."}

    # Other formats
    proxy.format(ProxyFormat.CURL)  # ["-x", "http://..."]
    proxy.format(ProxyFormat.HTTPX)  # {"http://": "...", "https://": "..."}


if __name__ == "__main__":
    main()
