import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from .models.proxy import Proxy

if TYPE_CHECKING:
    from .algorithms import Algorithm


@dataclass
class ProxyConfig:
    """Provides standard shared configuration options for all proxy providers.

    Example:

    .. code-block:: python

        from proxyproviders import Webshare, ProxyConfig

        config = ProxyConfig(refresh_interval=5)
        proxy_provider = Webshare(api_key="your-api-key", config=config)
    """

    refresh_interval: float = 600
    """Duration in seconds after which the proxy list is refreshed to fetch new proxies.
    Set to 0 to disable automatic refreshing after the initial fetch."""


class ProxyProvider(ABC):
    """
    Base class for all proxy providers that provides shared functionality across all providers.

    You'll need to use a specific provider to fetch proxies and this shouldn't directly be initialized. However, this class is useful for
    type hinting and for creating custom providers that are not included in the library, although consider contributing them to the library if you are making them.

    :param config: Configuration for the proxy provider. View the ProxyConfig class docs for more information.
    """

    def __init__(self, config: Optional[ProxyConfig] = None):
        if config is None:
            config = ProxyConfig()

        self.config: ProxyConfig = config
        self._proxies: Optional[List[Proxy]] = None
        self._last_refresh: Optional[datetime] = None
        self._lock = threading.Lock()

        # Initialize default algorithm (RoundRobin for state persistence)
        from .algorithms import RoundRobin

        self._default_algorithm = RoundRobin()

    def list_proxies(self, force_refresh: bool = False) -> List[Proxy]:
        """
        Returns the stored proxies.
        If a format function is provided, it applies that function to each proxy.

        :param force_refresh: If True, fetches new proxies even if the list is not considered stale.
        """
        if force_refresh or self.should_refresh() or not self._proxies:
            proxies = self._fetch_proxies()
            self._set_proxies(proxies)

        with self._lock:
            return list(self._proxies) if self._proxies else []

    def get_proxy(self, algorithm: Optional["Algorithm"] = None) -> Proxy:
        """Get a single proxy using the specified selection algorithm.

        :param algorithm: Selection algorithm to use. If None, uses the provider's default RoundRobin algorithm.
        :return: Selected proxy
        :raises ValueError: If no proxies are available

        Example:
            >>> from proxyproviders import Webshare
            >>> from proxyproviders.algorithms import Random, RoundRobin
            >>>
            >>> provider = Webshare(api_key="your-key")
            >>>
            >>> # Uses default RoundRobin (cycles through proxies)
            >>> proxy = provider.get_proxy()
            >>>
            >>> # Uses Random selection
            >>> proxy = provider.get_proxy(Random())
            >>>
            >>> # One-liner with requests
            >>> import requests
            >>> from proxyproviders.models.proxy import ProxyFormat
            >>> requests.get("https://httpbin.org/ip", proxies=provider.get_proxy().format(ProxyFormat.REQUESTS))
        """
        proxies = self.list_proxies()
        if not proxies:
            raise ValueError("No proxies available from provider")

        if algorithm is None:
            algorithm = self._default_algorithm

        return algorithm.select(proxies)

    #
    # Internal Methods
    #
    @abstractmethod
    def _fetch_proxies(self) -> List[Proxy]:
        """Fetch proxies from the provider implementation.
        This is not meant to be called directly, as it will always pull from the API even if not stale.
        """
        pass

    def should_refresh(self) -> bool:
        """Returns True if the proxy list should be refreshed based on the refresh_interval."""
        if self._proxies is None or self._last_refresh is None:
            return True

        if self.config.refresh_interval > 0:
            with self._lock:
                return (
                    datetime.now() - self._last_refresh
                ).total_seconds() >= self.config.refresh_interval

        return False

    def _set_proxies(self, proxies: List[Proxy]):
        """Sets the list of proxies and updates the last refresh time."""
        with self._lock:
            self._proxies = proxies
            self._last_refresh = datetime.now()
