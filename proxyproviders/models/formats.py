"""Converters between :class:`~proxyproviders.models.proxy.Proxy` and the shapes that HTTP
clients, browsers and tools expect.

Each output format is one small function registered in ``_FORMATTERS``. Adding a format
means adding a :class:`ProxyFormat` member and a function here; nothing else changes.
Parsing the other way (text to proxy fields) lives in :func:`parse_proxy_string`.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union
from urllib.parse import unquote, urlsplit

if TYPE_CHECKING:
    from .proxy import Proxy

FormattedProxy = Union[str, Dict[str, str], List[str]]
"""Every shape :meth:`Proxy.format` can return."""

# Schemes a proxy can be reached over that are not plain HTTP proxies.
SOCKS_SCHEMES = ("socks5", "socks5h", "socks4", "socks4a")
# URL schemes of the *target* request that HTTP clients key their proxy maps on.
TARGET_SCHEMES = ("http", "https")


class ProxyFormat(Enum):
    """Supported proxy output formats."""

    REQUESTS = "requests"
    """``{"http": url, "https": url}`` for the ``proxies=`` argument of requests"""

    CURL = "curl"
    """``["-x", url]`` arguments for the curl command line"""

    HTTPX = "httpx"
    """URL string for the ``proxy=`` argument of ``httpx.Client`` / ``httpx.AsyncClient``"""

    AIOHTTP = "aiohttp"
    """URL string for the ``proxy=`` argument of aiohttp requests and sessions"""

    PLAYWRIGHT = "playwright"
    """``{"server", "username", "password"}`` for the ``proxy=`` option of Playwright"""

    URL = "url"
    """``scheme://username:password@host:port`` URL string"""

    SCRAPY = "scrapy"
    """URL string for ``Request(meta={"proxy": ...})`` in Scrapy"""

    URLLIB = "urllib"
    """``{"http": url, "https": url}`` for ``urllib.request.ProxyHandler``"""

    ENV = "env"
    """``HTTP_PROXY`` / ``HTTPS_PROXY`` (and ``ALL_PROXY`` for SOCKS) environment variables,
    in upper and lower case, for subprocesses and tools that read them"""

    HOST_PORT_USER_PASS = "host_port_user_pass"
    """``host:port:username:password``, the plain-text line many proxy tools import"""


def host_for_url(host: str) -> str:
    """An IPv6 address needs square brackets wherever it is followed by ``:port``."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def _format_url(proxy: "Proxy", **kwargs: Any) -> str:
    return proxy.to_url(kwargs.get("protocol"))


def _format_proxy_url(proxy: "Proxy", **kwargs: Any) -> str:
    """Clients that take one proxy URL and use it for every request."""
    return proxy.to_url()


def _format_scheme_map(proxy: "Proxy", **kwargs: Any) -> Dict[str, str]:
    """Format proxy for requests and urllib.

    The keys are the schemes of the *target* URL that the client matches on, so only
    ``http``/``https`` are taken from the proxy's ``protocols``; SOCKS schemes there
    never become keys. A proxy that lists just one of them gets just that key, and
    requests to the other scheme are not proxied. Pass ``protocols`` to choose the
    keys yourself. The value is how to reach the proxy, which is where a SOCKS scheme
    belongs.
    """
    protocols: Optional[List[str]] = kwargs.get("protocols")
    if protocols is None:
        supported = [p for p in (proxy.protocols or []) if p in TARGET_SCHEMES]
        protocols = supported or list(TARGET_SCHEMES)
    proxy_url = proxy.to_url()
    return {protocol: proxy_url for protocol in protocols}


def _format_curl(proxy: "Proxy", **kwargs: Any) -> List[str]:
    return ["-x", proxy.to_url()]


def _format_playwright(proxy: "Proxy", **kwargs: Any) -> Dict[str, str]:
    # Playwright wants the scheme in "server", e.g. 'http://ip:port' or 'socks5://ip:port'
    protocol = kwargs.get("protocol", "http")

    if proxy.protocols and protocol not in proxy.protocols:
        # The requested protocol is not one the proxy supports, so use its first
        protocol = proxy.protocols[0]

    host = host_for_url(proxy.proxy_address)
    playwright_proxy = {"server": f"{protocol}://{host}:{proxy.port}"}

    if proxy.username and proxy.password:
        playwright_proxy["username"] = proxy.username
        playwright_proxy["password"] = proxy.password

    return playwright_proxy


def _format_env(proxy: "Proxy", **kwargs: Any) -> Dict[str, str]:
    proxy_url = proxy.to_url()
    names = ["HTTP_PROXY", "HTTPS_PROXY"]
    if proxy.scheme in SOCKS_SCHEMES:
        names.append("ALL_PROXY")
    env: Dict[str, str] = {}
    for name in names:
        # Tools disagree on case (curl only reads lowercase http_proxy), so set both
        env[name] = proxy_url
        env[name.lower()] = proxy_url
    return env


def _format_host_port_user_pass(proxy: "Proxy", **kwargs: Any) -> str:
    parts = [host_for_url(proxy.proxy_address), str(proxy.port)]
    if proxy.username or proxy.password:
        parts += [proxy.username, proxy.password]
    return ":".join(parts)


_FORMATTERS: Dict[ProxyFormat, Callable[..., FormattedProxy]] = {
    ProxyFormat.URL: _format_url,
    ProxyFormat.REQUESTS: _format_scheme_map,
    ProxyFormat.URLLIB: _format_scheme_map,
    ProxyFormat.CURL: _format_curl,
    ProxyFormat.HTTPX: _format_proxy_url,
    ProxyFormat.AIOHTTP: _format_proxy_url,
    ProxyFormat.SCRAPY: _format_proxy_url,
    ProxyFormat.PLAYWRIGHT: _format_playwright,
    ProxyFormat.ENV: _format_env,
    ProxyFormat.HOST_PORT_USER_PASS: _format_host_port_user_pass,
}


def format_proxy(
    proxy: "Proxy", format_type: Union[ProxyFormat, str], **kwargs: Any
) -> FormattedProxy:
    """Format ``proxy`` as ``format_type``. See :meth:`Proxy.format`."""
    # Convert to ProxyFormat enum, handling both string and enum inputs
    if isinstance(format_type, str):
        try:
            format_type = ProxyFormat(format_type)
        except ValueError:
            raise ValueError(
                f"Invalid format type: '{format_type}'. Valid options are: {[f.value for f in ProxyFormat]}"
            ) from None
    elif not isinstance(format_type, ProxyFormat):
        raise ValueError(  # pyright: ignore[reportUnreachable] this is actually reachable
            f"Invalid format type: {type(format_type).__name__}. Expected ProxyFormat enum or string."
        )

    return _FORMATTERS[format_type](proxy, **kwargs)


def _protocols_for_scheme(scheme: str) -> List[str]:
    scheme = scheme.lower()
    if scheme == "http":
        return list(TARGET_SCHEMES)
    if scheme in SOCKS_SCHEMES:
        return [scheme]
    if scheme == "https":
        raise ValueError(
            "An 'https://' proxy URL means TLS to the proxy itself, which Proxy does not "
            "model. Proxies that carry HTTPS traffic are normally written 'http://'."
        )
    raise ValueError(
        f"Unsupported proxy scheme '{scheme}'. Use http or one of {list(SOCKS_SCHEMES)}."
    )


def _parse_port(text: str, source: str) -> int:
    try:
        port = int(text)
    except ValueError:
        raise ValueError(f"Invalid port '{text}' in proxy '{source}'") from None
    if not 0 < port < 65536:
        raise ValueError(f"Port {port} is out of range in proxy '{source}'")
    return port


def _check_host(host: str, source: str) -> str:
    if not host or any(character.isspace() for character in host):
        raise ValueError(f"Invalid host in proxy '{source}'")
    return host


def _split_host_port_line(text: str) -> Optional[List[str]]:
    """Split ``host:port[:user:pass]`` into its pieces, or None if it is not that form.

    The host may be a bracketed IPv6 address. The password is everything after the third
    separator, so it may contain ``:`` and ``@``.
    """
    if text.startswith("["):
        host, bracket, rest = text[1:].partition("]")
        if not bracket or not rest.startswith(":"):
            return None
        pieces = [host, *rest[1:].split(":", 2)]
    else:
        pieces = text.split(":", 3)

    if len(pieces) not in (2, 4) or not pieces[1].isdigit():
        return None
    return pieces


def parse_proxy_string(text: str) -> Dict[str, Any]:
    """Parse one proxy written as text into the fields of a :class:`Proxy`.

    Accepted forms:

    * a URL: ``http://user:pass@host:port``, ``socks5://host:port``
    * ``host:port:user:pass``, the line format many providers export, and ``host:port``
    * ``user:pass@host:port`` (treated as http)

    Percent-encoded credentials in a URL are decoded. In ``host:port:user:pass`` the
    password is everything after the third colon, so it may itself contain ``:`` or
    ``@``. An IPv6 host is written in square brackets, e.g. ``[2001:db8::1]:8080``.

    :raises ValueError: if the text is not one of these forms
    """
    source = text
    text = text.strip()
    if not text:
        raise ValueError("Cannot parse an empty proxy string")

    if "://" not in text:
        # Why: tried before the URL form so an '@' in a password is not read as user@host
        pieces = _split_host_port_line(text)
        if pieces is not None:
            return {
                "proxy_address": _check_host(pieces[0], source),
                "port": _parse_port(pieces[1], source),
                "username": pieces[2] if len(pieces) == 4 else "",
                "password": pieces[3] if len(pieces) == 4 else "",
                "protocols": list(TARGET_SCHEMES),
            }
        if "@" not in text:
            raise ValueError(
                f"Cannot parse proxy '{source}'. Expected a URL, 'host:port' or "
                "'host:port:username:password'."
            )

    url = text if "://" in text else f"http://{text}"
    parts = urlsplit(url)
    protocols = _protocols_for_scheme(parts.scheme)
    try:
        port = parts.port
    except ValueError:
        raise ValueError(f"Invalid port in proxy '{source}'") from None
    if not parts.hostname or port is None:
        raise ValueError(f"Proxy '{source}' needs both a host and a port")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError(
            f"Proxy '{source}' has a path or query, which a proxy address cannot have"
        )
    return {
        "proxy_address": _check_host(parts.hostname, source),
        "port": _parse_port(str(port), source),
        "username": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "protocols": protocols,
    }
