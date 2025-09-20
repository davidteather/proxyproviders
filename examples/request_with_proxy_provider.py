"""Examples showing provider-agnostic proxy usage."""

import requests

from proxyproviders import BrightData, ProxyProvider, Webshare
from proxyproviders.algorithms import First, Random, RoundRobin
from proxyproviders.models.proxy import ProxyFormat


def make_request_with_proxy(provider: ProxyProvider):
    """Make HTTP request through any proxy provider."""
    proxy = provider.get_proxy()
    response = requests.get(
        "https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS)
    )
    return response.json()


def algorithm_examples():
    """Show different algorithms with same provider."""
    provider = Webshare(api_key="your_api_key")

    # Default RoundRobin
    provider.get_proxy()

    # Random selection
    provider.get_proxy(Random())

    # Always first proxy
    provider.get_proxy(First())

    # Reusable RoundRobin (maintains state)
    round_robin = RoundRobin()
    provider.get_proxy(round_robin)
    provider.get_proxy(round_robin)  # Next in sequence


def one_liner_examples():
    """One-liner HTTP requests through proxy."""
    provider = Webshare(api_key="your_api_key")

    # Default algorithm
    requests.get(
        "https://httpbin.org/ip",
        proxies=provider.get_proxy().format(ProxyFormat.REQUESTS),
    )

    # With specific algorithm
    requests.get(
        "https://httpbin.org/ip",
        proxies=provider.get_proxy(Random()).format(ProxyFormat.REQUESTS),
    )


def main():
    # Works with any provider
    webshare = Webshare(api_key="your_api_key")
    brightdata = BrightData(api_key="your_api_key", zone="your_zone")

    # Same function works with different providers
    make_request_with_proxy(webshare)
    make_request_with_proxy(brightdata)

    # Algorithm examples
    algorithm_examples()

    # One-liner usage
    one_liner_examples()


if __name__ == "__main__":
    main()
