import pytest
from proxyproviders.exceptions import ProxyFetchException, ProxyInvalidResponseException

def test_proxy_fetch_exception():
    """
    Test that ProxyFetchException stores the correct message and status code.
    """
    ex = ProxyFetchException("Fetch error", status_code=500)
    assert "Fetch error" in str(ex)
    assert ex.status_code == 500

def test_proxy_invalid_response_exception():
    """
    Test that ProxyInvalidResponseException correctly formats its message.
    """
    response = '{"error": "Invalid API Key"}'
    ex = ProxyInvalidResponseException(response)
    assert "Invalid response received" in str(ex)
