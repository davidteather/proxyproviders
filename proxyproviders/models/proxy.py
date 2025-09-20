from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union


class ProxyFormat(Enum):
    """Supported proxy output formats."""

    REQUESTS = "requests"
    """Requests format, for use in requests library HTTP calls"""

    CURL = "curl"
    """CURL format, for use in curl commands"""

    HTTPX = "httpx"
    """HTTPX format, for use in httpx library HTTP calls"""

    AIOHTTP = "aiohttp"
    """AIOHTTP format, for use in aiohttp library HTTP calls"""

    URL = "url"
    """URL format, for use in URL strings"""


@dataclass
class Proxy:
    """Our shared data model for a proxy object across all providers."""

    id: str
    """A unique identifier for the proxy"""

    username: str
    """The username required for authenticating with the proxy"""

    password: str
    """The password required for authenticating with the proxy"""

    proxy_address: str
    """The IP address or domain name of the proxy"""

    port: int
    """The port number through which the proxy connection is established"""

    country_code: Optional[str] = None
    """The country code where the proxy is located, e.g., 'US', 'FR'. Optional"""

    city_name: Optional[str] = None
    """The city name where the proxy is located, e.g., 'New York', 'Paris'. Optional"""

    created_at: Optional[datetime] = None
    """The timestamp when the proxy was created. Optional"""

    protocols: Optional[List[str]] = None
    """A list of connection protocols supported by the proxy, e.g., ['http', 'https']"""

    def to_url(self, protocol: str = "http") -> str:
        """Convert proxy to URL format for use with HTTP clients.

        :param protocol: The protocol to use in the URL (default: 'http')
        :return: Proxy URL in format 'protocol://username:password@host:port'

        Example:
            >>> proxy.to_url()
            'http://user:pass@192.168.1.1:8080'
            >>> proxy.to_url('https')
            'https://user:pass@192.168.1.1:8080'
        """
        return f"{protocol}://{self.username}:{self.password}@{self.proxy_address}:{self.port}"

    def format(
        self, format_type: Union[ProxyFormat, str] = ProxyFormat.URL, **kwargs
    ) -> Union[str, Dict[str, str], List[str]]:
        """Format proxy for different HTTP clients and tools.

        :param format_type: Output format (default: URL string)
        :param kwargs: Format-specific options
        :return: Formatted proxy data

        Examples:
            >>> proxy.format()  # Default URL string
            'http://user:pass@192.168.1.1:8080'

            >>> proxy.format(ProxyFormat.REQUESTS)
            {'http': 'http://user:pass@192.168.1.1:8080', 'https': 'http://user:pass@192.168.1.1:8080'}

            >>> proxy.format('curl')  # String also works
            ['-x', 'http://user:pass@192.168.1.1:8080']

            >>> proxy.format(ProxyFormat.HTTPX)
            {'http://': 'http://user:pass@192.168.1.1:8080', 'https://': 'http://user:pass@192.168.1.1:8080'}
        """
        if isinstance(format_type, str):
            format_type = ProxyFormat(format_type)

        if format_type == ProxyFormat.URL:
            protocol = kwargs.get("protocol", "http")
            return self.to_url(protocol)

        elif format_type == ProxyFormat.REQUESTS:
            protocols = kwargs.get("protocols", self.protocols or ["http", "https"])
            proxy_url = self.to_url("http")
            return {protocol: proxy_url for protocol in protocols}

        elif format_type == ProxyFormat.CURL:
            return ["-x", self.to_url("http")]

        elif format_type == ProxyFormat.HTTPX:
            # httpx uses 'http://' and 'https://' as keys
            proxy_url = self.to_url("http")
            return {"http://": proxy_url, "https://": proxy_url}

        elif format_type == ProxyFormat.AIOHTTP:
            # aiohttp takes a single URL string
            return self.to_url("http")

        else:
            raise ValueError(f"Unsupported format: {format_type}")
