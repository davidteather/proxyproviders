from typing import Optional

"""
All custom exceptions for the ProxyProvider classes are defined here.
"""


class ProxyProviderException(Exception):
    """Base class for all ProxyProvider errors."""

    pass


class ProxyFetchException(ProxyProviderException):
    """Raised when there is an error fetching proxies from the provider."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ProxyConversionException(ProxyProviderException):
    """Raised when there is an error converting proxy data to a standardized format."""

    pass


class ProxyInvalidResponseException(ProxyProviderException):
    """Raised when the provider returns an invalid response."""

    def __init__(self, response: str):
        self.response = response
        self.message = f"Invalid response received: {response}"
        super().__init__(self.message)
