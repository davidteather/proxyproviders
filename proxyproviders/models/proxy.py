from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union, overload
from urllib.parse import quote

from .formats import (
    SOCKS_SCHEMES,
    TARGET_SCHEMES,
    FormattedProxy,
    ProxyFormat,
    format_proxy,
    host_for_url,
    parse_proxy_string,
)

__all__ = ["FormattedProxy", "Proxy", "ProxyFormat"]


@dataclass
class Proxy:
    """Our shared data model for a proxy object across all providers."""

    id: str
    """A unique identifier for the proxy"""

    username: str
    """The username required for authenticating with the proxy"""

    password: str = field(repr=False)
    """The password required for authenticating with the proxy. Left out of ``repr()`` so
    printing or logging a proxy does not expose it."""

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

    @classmethod
    def from_string(cls, text: str, id: Optional[str] = None, **fields: Any) -> "Proxy":
        """Build a proxy from text, for proxies you already have as a list or a file.

        Accepted forms:

        * a URL: ``http://user:pass@host:port``, ``socks5://host:port``
        * ``user:pass@host:port`` and ``host:port`` (treated as http)
        * ``host:port:user:pass``, the line format many providers export

        :param text: The proxy to parse
        :param id: Identifier for the proxy. Defaults to ``host:port``.
        :param fields: Any other :class:`Proxy` fields to set, e.g. ``country_code="US"``
        :raises ValueError: If the text is not one of the accepted forms

        Example:
            >>> Proxy.from_string("203.0.113.7:8080:user:pass").to_url()
            'http://user:pass@203.0.113.7:8080'
        """
        parsed = parse_proxy_string(text)
        if id is None:
            id = f"{parsed['proxy_address']}:{parsed['port']}"
        return cls(id=id, **{**parsed, **fields})

    @classmethod
    def from_url(cls, url: str, id: Optional[str] = None, **fields: Any) -> "Proxy":
        """Build a proxy from a URL such as ``http://user:pass@host:port``.

        The reverse of :meth:`to_url`: percent-encoded credentials are decoded. See
        :meth:`from_string`, which this is an alias of, for every accepted form.
        """
        return cls.from_string(url, id=id, **fields)

    @property
    def scheme(self) -> str:
        """The URL scheme used to connect to this proxy.

        ``protocols`` lists what the proxy supports. A proxy that supports ``http`` or
        ``https`` (or does not say) is reached over ``http``. A SOCKS-only proxy, e.g.
        ``protocols=["socks5"]``, is reached over that SOCKS scheme.
        """
        if not self.protocols:
            return "http"
        if any(protocol in TARGET_SCHEMES for protocol in self.protocols):
            return "http"
        for protocol in self.protocols:
            if protocol in SOCKS_SCHEMES:
                return protocol
        return "http"

    def to_url(self, protocol: Optional[str] = None) -> str:
        """Convert proxy to URL format for use with HTTP clients.

        :param protocol: The protocol to use in the URL. Defaults to :attr:`scheme`, which is
            ``http`` unless the proxy only supports SOCKS.
        :return: Proxy URL in format 'protocol://username:password@host:port'.
            The username and password are percent-encoded, so characters such
            as ``@``, ``:``, ``#`` or ``/`` in them do not change where the URL
            points. A proxy with no username and no password gives
            'protocol://host:port'.

        Example:
            >>> proxy.to_url()
            'http://user:pass@192.168.1.1:8080'
            >>> proxy.to_url('https')
            'https://user:pass@192.168.1.1:8080'
        """
        if protocol is None:
            protocol = self.scheme
        host = host_for_url(self.proxy_address)
        if not self.username and not self.password:
            return f"{protocol}://{host}:{self.port}"
        username = quote(self.username, safe="")
        password = quote(self.password, safe="")
        return f"{protocol}://{username}:{password}@{host}:{self.port}"

    @overload
    def format(
        self,
        format_type: Literal[
            ProxyFormat.URL,
            ProxyFormat.HTTPX,
            ProxyFormat.AIOHTTP,
            ProxyFormat.SCRAPY,
            ProxyFormat.HOST_PORT_USER_PASS,
            "url",
            "httpx",
            "aiohttp",
            "scrapy",
            "host_port_user_pass",
        ] = ...,
        **kwargs: Any,
    ) -> str: ...

    @overload
    def format(
        self,
        format_type: Literal[
            ProxyFormat.REQUESTS,
            ProxyFormat.URLLIB,
            ProxyFormat.PLAYWRIGHT,
            ProxyFormat.ENV,
            "requests",
            "urllib",
            "playwright",
            "env",
        ],
        **kwargs: Any,
    ) -> Dict[str, str]: ...

    @overload
    def format(
        self, format_type: Literal[ProxyFormat.CURL, "curl"], **kwargs: Any
    ) -> List[str]: ...

    @overload
    def format(
        self, format_type: Union[ProxyFormat, str], **kwargs: Any
    ) -> FormattedProxy: ...

    def format(
        self, format_type: Union[ProxyFormat, str] = ProxyFormat.URL, **kwargs: Any
    ) -> FormattedProxy:
        """Format proxy for different HTTP clients and tools.

        A SOCKS-only proxy (``protocols=["socks5"]``) is formatted with its SOCKS scheme.
        Your HTTP client needs SOCKS support for that: ``requests[socks]`` or
        ``httpx[socks]``. aiohttp and Scrapy have no built-in SOCKS support.

        :param format_type: Output format (default: URL string). See :class:`ProxyFormat`
            for every format and what it is passed to.
        :param kwargs: Format-specific options: ``protocol`` for ``URL`` and
            ``PLAYWRIGHT``, ``protocols`` for ``REQUESTS`` and ``URLLIB``
        :return: Formatted proxy data

        Examples:
            >>> proxy.format()  # Default URL string
            'http://user:pass@192.168.1.1:8080'

            >>> proxy.format(ProxyFormat.REQUESTS)  # requests.get(url, proxies=...)
            {'http': 'http://user:pass@192.168.1.1:8080', 'https': 'http://user:pass@192.168.1.1:8080'}

            >>> proxy.format('curl')  # String also works
            ['-x', 'http://user:pass@192.168.1.1:8080']

            >>> proxy.format(ProxyFormat.HTTPX)  # httpx.Client(proxy=...)
            'http://user:pass@192.168.1.1:8080'

            >>> proxy.format(ProxyFormat.PLAYWRIGHT)  # browser.new_context(proxy=...)
            {'server': 'http://192.168.1.1:8080', 'username': 'user', 'password': 'pass'}

            >>> proxy.format(ProxyFormat.HOST_PORT_USER_PASS)
            '192.168.1.1:8080:user:pass'
        """
        return format_proxy(self, format_type, **kwargs)
