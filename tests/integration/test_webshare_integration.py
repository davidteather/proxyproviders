import os
import pytest
from proxyproviders.providers.webshare import Webshare

# Skip integration tests unless explicitly enabled
skip_integration = pytest.mark.skipif(
    not (os.getenv("RUN_INTEGRATION_TESTS") and os.getenv("WEBSHARE_API_KEY")),
    reason="Integration tests require RUN_INTEGRATION_TESTS flag and a valid WEBSHARE_API_KEY"
)

@skip_integration
def test_webshare_integration():
    """
    Integration test: Perform a real API call to Webshare.
    This sanity test ensures that the provider's structure and conversion functions
    work correctly when interacting with the live API.
    """
    api_key = os.getenv("WEBSHARE_API_KEY")
    provider = Webshare(api_key=api_key)

    proxies = provider.list_proxies(force_refresh=True)

    assert isinstance(proxies, list)
    if proxies:
        for proxy in proxies:
            assert hasattr(proxy, 'port')
            assert isinstance(proxy.port, int)
