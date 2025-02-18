import os
import pytest
from proxyproviders.providers.webshare import Webshare
from proxyproviders.providers.brightdata import BrightData
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
