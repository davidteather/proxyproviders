from pathlib import Path
from typing import Iterable, List, Optional, Union

from ..models.proxy import Proxy
from ..proxy_provider import ProxyConfig, ProxyProvider


class ProxyList(ProxyProvider):
    """A provider for proxies you already have, from any vendor.

    Use it when your vendor has no provider here yet, or when you manage the list
    yourself. You get the same interface as every other provider: selection algorithms,
    output formats, failure reporting and :class:`~proxyproviders.session.RotatingSession`.

    :param proxies: The proxies, each either a :class:`~proxyproviders.models.proxy.Proxy`
        or text in any form :meth:`Proxy.from_string` accepts: a URL such as
        ``http://user:pass@host:port`` or ``socks5://host:port``, or ``host:port:user:pass``
    :param config: Configuration for the proxy provider. View the ProxyConfig class docs for more information.
    :raises ValueError: If an entry cannot be parsed, or the list is empty

    Example:

    .. code-block:: python

        from proxyproviders import ProxyList

        provider = ProxyList(
            [
                "http://user:pass@203.0.113.7:8080",
                "203.0.113.8:8080:user:pass",
                "socks5://user:pass@203.0.113.9:1080",
            ]
        )

        proxy = provider.get_proxy()

        # Or one proxy per line from a file, ignoring blank lines and # comments
        provider = ProxyList.from_file("proxies.txt")
    """

    def __init__(
        self,
        proxies: Iterable[Union[str, Proxy]],
        config: Optional[ProxyConfig] = None,
    ):
        super().__init__(config)
        self._source: List[Proxy] = [
            p if isinstance(p, Proxy) else Proxy.from_string(p) for p in proxies
        ]
        if not self._source:
            raise ValueError("ProxyList needs at least one proxy")

    @classmethod
    def from_file(
        cls, path: Union[str, Path], config: Optional[ProxyConfig] = None
    ) -> "ProxyList":
        """Load proxies from a text file with one proxy per line.

        Blank lines and lines starting with ``#`` are skipped.

        :param path: Path to the file
        :param config: Configuration for the proxy provider
        """
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
        entries = [line.strip() for line in lines]
        return cls(
            [entry for entry in entries if entry and not entry.startswith("#")],
            config=config,
        )

    def _fetch_proxies(self) -> List[Proxy]:
        return list(self._source)
