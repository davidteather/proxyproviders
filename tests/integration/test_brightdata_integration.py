import os
import pytest
import responses
from proxyproviders.providers.brightdata import BrightData
from proxyproviders.exceptions import (
    ProxyFetchException,
    ProxyConversionException,
    ProxyInvalidResponseException,
)
from proxyproviders.models.proxy import Proxy

skip_integration = pytest.mark.skipif(
    not (
        os.getenv("RUN_INTEGRATION_TESTS")
        and os.getenv("BRIGHTDATA_API_KEY")
    ),
    reason="Integration tests require RUN_INTEGRATION_TESTS flag and valid BRIGHTDATA_API_KEY",
)

@skip_integration
def test_brightdata_integration():
    """
    Integration test: Perform a real API call to BrightData.
    This sanity test ensures that the provider's structure and conversion functions
    work correctly when interacting with the live API.
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    provider = BrightData(api_key=api_key, zone="static")
    
    # List proxies; note that behavior will vary based on provider.use_super_proxy.
    proxies = provider.list_proxies(force_refresh=True)
    
    assert isinstance(proxies, list)
    # If using super proxy mode, one proxy is expected; otherwise, there may be many.
    if provider.use_super_proxy:
        assert len(proxies) == 1
        proxy = proxies[0]
        assert hasattr(proxy, "port")
        assert isinstance(proxy.port, (int, str))
    else:
        for proxy in proxies:
            assert hasattr(proxy, "port")
            assert isinstance(proxy.port, (int, str))