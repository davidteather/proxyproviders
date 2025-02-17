import os
import pytest
import responses
from proxyproviders.providers.webshare import Webshare
from proxyproviders.exceptions import ProxyFetchException, ProxyInvalidResponseException, ProxyConversionException
from proxyproviders.models.proxy import Proxy

@pytest.fixture
def mock_webshare():
    """Fixture to create a Webshare provider instance for unit tests."""
    api_key = os.getenv("WEBSHARE_API_KEY", "test-api-key")
    return Webshare(api_key=api_key)

@responses.activate
def test_fetch_proxies_success(mock_webshare):
    """
    Unit test: Fetch proxies successfully using a mocked API response.
    """
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list",
        json={
            "results": [
                {
                    "id": "1",
                    "username": "user1",
                    "password": "pass1",
                    "proxy_address": "192.168.1.1",
                    "port": 8080,
                    "country_code": "US",
                    "city_name": "New York",
                    "created_at": "2023-05-10T12:34:56",
                }
            ],
            "next": None,
        },
        status=200
    )
    proxies = mock_webshare._fetch_proxies()
    assert isinstance(proxies, list)
    assert len(proxies) == 1
    proxy = proxies[0]
    assert isinstance(proxy, Proxy)
    assert proxy.proxy_address == "192.168.1.1"

@responses.activate
def test_fetch_proxies_pagination(mock_webshare):
    """
    Unit test: Check that proxies are fetched correctly across multiple pages.
    """
    # Page 1
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list?mode=direct&page=1&page_size=100",
        json={
            "results": [
                {
                    "id": "1",
                    "username": "user1",
                    "password": "pass1",
                    "proxy_address": "192.168.1.1",
                    "port": 8080,
                    "country_code": "US",
                    "city_name": "New York",
                    "created_at": "2023-05-10T12:34:56",
                }
            ],
            "next": "https://proxy.webshare.io/api/v2/proxy/list?mode=direct&page=2&page_size=100",
        },
        status=200
    )
    
    # Page 2
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list?mode=direct&page=2&page_size=100",
        json={
            "results": [
                {
                    "id": "2",
                    "username": "user2",
                    "password": "pass2",
                    "proxy_address": "192.168.1.2",
                    "port": 8080,
                    "country_code": "US",
                    "city_name": "Los Angeles",
                    "created_at": "2023-05-10T12:34:56",
                }
            ],
            "next": None,
        },
        status=200
    )
    
    proxies = mock_webshare._fetch_proxies()
    
    assert isinstance(proxies, list)
    assert len(proxies) == 2
    
    assert proxies[0].proxy_address == "192.168.1.1" 
    assert proxies[1].proxy_address == "192.168.1.2"

@responses.activate
def test_fetch_proxies_invalid_response(mock_webshare):
    """
    Unit test: Check that an invalid API response raises the appropriate exception.
    """
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list",
        json={"error": "Invalid API Key"},
        status=403
    )
    with pytest.raises(ProxyFetchException):
        mock_webshare._fetch_proxies()

def test_sanity_check_webshare_structure(mock_webshare):
    """
    Sanity test: Ensures that the Webshare provider returns a list via list_proxies(),
    even if no proxies have been fetched.
    """
    # Force internal state to simulate an empty proxy list
    mock_webshare._proxies = []
    result = mock_webshare.list_proxies()
    assert isinstance(result, list)

@responses.activate
def test_fetch_proxies_empty_list(mock_webshare):
    """
    Unit test: Fetch proxies with a bad response.
    """
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list",
        json={},
        status=200
    )

    with pytest.raises(ProxyInvalidResponseException):
        mock_webshare._fetch_proxies()

@responses.activate
def test_bad_proxy_format_response(mock_webshare):
    """
    Unit test: Fetch proxies with a bad response.
    """
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list",
        json={
            "results": [
                {
                    "error": "could not retrieve"
                }
            ],
            "next": None,
        },
        status=200
    )

    with pytest.raises(ProxyConversionException):
        mock_webshare._fetch_proxies()

@responses.activate
def test_invalid_proxy_timestamp(mock_webshare):
    """
    Unit test: Fetch proxies with a bad response.
    """
    responses.add(
        responses.GET,
        "https://proxy.webshare.io/api/v2/proxy/list",
        json={
            "results": [
                {
                    "id": "1",
                    "username": "user1",
                    "password": "pass1",
                    "proxy_address": "192.168.1.1",
                    "port": 8080,
                    "country_code": "US",
                    "city_name": "New York",
                    "created_at": "this proxy was never created",
                },
                {
                    "id": "2",
                    "username": "user1",
                    "password": "pass1",
                    "proxy_address": "192.168.1.1",
                    "port": 8080,
                    "country_code": "US",
                    "city_name": "New York",
                }
            ],
            "next": None,
        },
        status=200
    )

    proxies = mock_webshare._fetch_proxies()

    assert isinstance(proxies, list)
    assert len(proxies) == 2

    proxy_invalid_created_at = proxies[0]
    assert isinstance(proxy_invalid_created_at, Proxy)
    assert proxy_invalid_created_at.created_at is None

    proxy_absent_created_at = proxies[1]
    assert isinstance(proxy_absent_created_at, Proxy)
    assert proxy_absent_created_at.created_at is None