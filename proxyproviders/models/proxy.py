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

    PLAYWRIGHT = "playwright"
    """Playwright format, for use in Playwright browser automation"""

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
        # Convert to ProxyFormat enum, handling both string and enum inputs
        if isinstance(format_type, str):
            try:
                format_type = ProxyFormat(format_type)
            except ValueError:
                raise ValueError(
                    f"Invalid format type: '{format_type}'. Valid options are: {[f.value for f in ProxyFormat]}"
                )
        elif not isinstance(format_type, ProxyFormat):
            raise ValueError(  # pyright: ignore[reportUnreachable] this is actually reachable
                f"Invalid format type: {type(format_type).__name__}. Expected ProxyFormat enum or string."
            )

        format_handlers = {
            ProxyFormat.URL: lambda: self.to_url(kwargs.get("protocol", "http")),
            ProxyFormat.REQUESTS: lambda: self._format_requests(kwargs),
            ProxyFormat.CURL: lambda: ["-x", self.to_url("http")],
            ProxyFormat.HTTPX: lambda: self._format_httpx(),
            ProxyFormat.AIOHTTP: lambda: self.to_url("http"),
            ProxyFormat.PLAYWRIGHT: lambda: self._format_playwright(**kwargs),
        }

        handler = format_handlers[format_type]
        return handler()

    def _format_requests(self, kwargs):
        """Format proxy for requests library."""
        protocols = kwargs.get("protocols", self.protocols or ["http", "https"])
        proxy_url = self.to_url("http")
        return {protocol: proxy_url for protocol in protocols}

    def _format_httpx(self):
        """Format proxy for httpx library."""
        proxy_url = self.to_url("http")
        return {"http://": proxy_url, "https://": proxy_url}

    def _format_playwright(self, **kwargs):
        """Format proxy for Playwright."""
        # Playwright expects server with protocol (e.g., 'http://ip:port', 'socks5://ip:port')
        # Allow protocol selection via kwargs, default to http
        protocol = kwargs.get("protocol", "http")

        # Validate protocol is supported by the proxy
        if self.protocols and protocol not in self.protocols:
            # If proxy has specific protocols, use the first available one
            protocol = self.protocols[0]

        playwright_proxy = {"server": f"{protocol}://{self.proxy_address}:{self.port}"}

        if self.username and self.password:
            playwright_proxy["username"] = self.username
            playwright_proxy["password"] = self.password

        return playwright_proxy
