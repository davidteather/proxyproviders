import os

import pytest

from proxyproviders.providers.brightdata import BrightData
from proxyproviders.providers.webshare import Webshare
from proxyproviders.proxy_provider import ProxyConfig


@pytest.fixture
def webshare_provider():
    """
    Fixture to initialize a Webshare provider using the API key from environment variables.
    If no key is provided, a dummy key ('test-api-key') is used for unit tests.
    """
    api_key = os.getenv("WEBSHARE_API_KEY", "test-api-key")
    return Webshare(api_key=api_key, config=ProxyConfig(refresh_interval=0))


@pytest.fixture
def brightdata_provider():
    """
    Fixture to create a BrightData provider instance for unit tests.
    """
    # Use dummy credentials for testing
    api_key = os.getenv("BRIGHTDATA_API_KEY", "test-brightdata-api-key")
    zone = "test-zone"
    return BrightData(api_key=api_key, zone=zone)


@pytest.fixture
def target():
    """A local HTTP server standing in for the site being requested."""
    from tests.local_servers import TargetServer

    server = TargetServer()
    yield server
    server.close()


@pytest.fixture
def http_proxy():
    """A local authenticated HTTP forward proxy."""
    from tests.local_servers import HttpProxyServer

    server = HttpProxyServer()
    yield server
    server.close()


@pytest.fixture
def make_http_proxy():
    """Factory for extra local proxies, all closed at the end of the test."""
    from tests.local_servers import HttpProxyServer

    servers = []

    def make(**kwargs):
        server = HttpProxyServer(**kwargs)
        servers.append(server)
        return server

    yield make
    for server in servers:
        server.close()
