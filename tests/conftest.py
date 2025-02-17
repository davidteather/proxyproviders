import os
import pytest
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
