import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .models.proxy import Proxy

if TYPE_CHECKING:
    from .algorithms import Algorithm

logger = logging.getLogger(__name__)


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

    timeout: float = 30
    """Timeout in seconds for each request to the provider's API, so a stalled connection
    raises instead of hanging forever."""

    refresh_retry_delay: float = 30
    """After an automatic refresh fails and the previous proxy list is served instead, wait
    this many seconds before trying the provider's API again."""

    failure_cooldown: float = 60
    """How long, in seconds, :meth:`ProxyProvider.get_proxy` avoids a proxy after it was
    passed to :meth:`ProxyProvider.report_failure`."""


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
        self._retry_refresh_after: Optional[datetime] = None
        # Proxies reported as failing, and when each may be handed out again
        self._cooldowns: Dict[Tuple[str, int, str], datetime] = {}
        # Guards the cached proxies and timestamps
        self._lock = threading.Lock()
        # Held while fetching, so concurrent callers trigger one fetch instead of one each
        self._refresh_lock = threading.Lock()

        # Initialize default algorithm (RoundRobin for state persistence)
        from .algorithms import RoundRobin

        self._default_algorithm = RoundRobin()

    def list_proxies(self, force_refresh: bool = False) -> List[Proxy]:
        """
        Returns the stored proxies, fetching them from the provider first when they are
        missing or older than ``refresh_interval``.

        Safe to call from several threads: when the list is stale only one thread fetches
        and the others wait for its result.

        If an automatic refresh fails and an earlier list is available, that list is
        returned and a warning is logged, so one failed call to the provider's API does not
        take your proxies away. The error is raised when there is nothing to fall back on,
        or when ``force_refresh`` is True.

        :param force_refresh: If True, fetches new proxies even if the list is not considered stale.
        """
        if force_refresh or self._refresh_due():
            with self._refresh_lock:
                # Another thread may have refreshed while this one waited for the lock
                if force_refresh or self._refresh_due():
                    self._refresh(force_refresh)

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

        # If every proxy is cooling down, handing one out beats failing outright
        candidates = self._without_cooling_down(proxies) or proxies

        if algorithm is None:
            algorithm = self._default_algorithm

        return algorithm.select(candidates)

    def report_failure(self, proxy: Proxy, cooldown: Optional[float] = None) -> None:
        """Tell the provider a proxy just failed, so :meth:`get_proxy` avoids it for a while.

        Nothing calls this for you unless you use
        :class:`~proxyproviders.session.RotatingSession`; it is how your own code feeds
        back a connection error, a ban or a bad response. The proxy stays in
        :meth:`list_proxies` and comes back into rotation once the cooldown has passed. If
        every proxy is cooling down, :meth:`get_proxy` still returns one.

        :param proxy: The proxy that failed
        :param cooldown: Seconds to avoid it for. Defaults to ``ProxyConfig.failure_cooldown``.

        Example:
            >>> proxy = provider.get_proxy()
            >>> try:
            ...     requests.get(url, proxies=proxy.format(ProxyFormat.REQUESTS), timeout=10)
            ... except requests.exceptions.ProxyError:
            ...     provider.report_failure(proxy)
        """
        if cooldown is None:
            cooldown = self.config.failure_cooldown
        with self._lock:
            self._cooldowns[self._health_key(proxy)] = datetime.now() + timedelta(
                seconds=cooldown
            )

    def report_success(self, proxy: Proxy) -> None:
        """Clear a failure reported for a proxy, putting it back into rotation right away."""
        with self._lock:
            self._cooldowns.pop(self._health_key(proxy), None)

    def available_proxies(self) -> List[Proxy]:
        """Like :meth:`list_proxies`, without the proxies currently cooling down after
        :meth:`report_failure`."""
        return self._without_cooling_down(self.list_proxies())

    #
    # Internal Methods
    #
    @abstractmethod
    def _fetch_proxies(self) -> List[Proxy]:
        """Fetch proxies from the provider implementation.
        This is not meant to be called directly, as it will always pull from the API even if not stale.
        """
        pass

    @staticmethod
    def _health_key(proxy: Proxy) -> Tuple[str, int, str]:
        # Not Proxy.id: gateway providers reuse one address with a username per exit
        return (proxy.proxy_address, proxy.port, proxy.username)

    def _without_cooling_down(self, proxies: List[Proxy]) -> List[Proxy]:
        now = datetime.now()
        with self._lock:
            if not self._cooldowns:
                return proxies
            self._cooldowns = {
                key: until for key, until in self._cooldowns.items() if until > now
            }
            cooling = set(self._cooldowns)
        return [p for p in proxies if self._health_key(p) not in cooling]

    def should_refresh(self) -> bool:
        """Returns True if the proxy list should be refreshed based on the refresh_interval."""
        with self._lock:
            if self._proxies is None or self._last_refresh is None:
                return True

            if self.config.refresh_interval > 0:
                return (
                    datetime.now() - self._last_refresh
                ).total_seconds() >= self.config.refresh_interval

            return False

    def _refresh_due(self) -> bool:
        """Whether list_proxies should call the provider now."""
        with self._lock:
            has_proxies = bool(self._proxies)
            retry_after = self._retry_refresh_after

        if has_proxies and retry_after is not None and datetime.now() < retry_after:
            # A recent refresh failed and the previous list is being served
            return False

        return self.should_refresh() or not has_proxies

    def _refresh(self, force_refresh: bool) -> None:
        """Fetches proxies and stores them. Must be called with _refresh_lock held."""
        try:
            proxies = self._fetch_proxies()
        except Exception:
            with self._lock:
                has_proxies = bool(self._proxies)
                if has_proxies and not force_refresh:
                    self._retry_refresh_after = datetime.now() + timedelta(
                        seconds=self.config.refresh_retry_delay
                    )
            if force_refresh or not has_proxies:
                raise
            logger.warning(
                "Refreshing proxies failed, serving the previous list. "
                "Retrying in %s seconds.",
                self.config.refresh_retry_delay,
                exc_info=True,
            )
            return

        self._set_proxies(proxies)

    def _set_proxies(self, proxies: List[Proxy]) -> None:
        """Sets the list of proxies and updates the last refresh time."""
        with self._lock:
            self._proxies = proxies
            self._last_refresh = datetime.now()
            self._retry_refresh_after = None
