"""Opt-in httpx transports that pick a proxy for every request, sync and async.

Nothing else in the package uses this module, and it is the only one that needs httpx:
``pip install "proxyproviders[httpx]"``.
"""

import threading
from typing import TYPE_CHECKING, Any, Collection, Dict, Optional, Tuple

try:
    import anyio.to_thread
    import httpx
except ImportError as error:  # pragma: no cover
    raise ImportError(
        "proxyproviders.httpx_transport needs httpx. Install it with: "
        'pip install "proxyproviders[httpx]"'
    ) from error

from .models.proxy import Proxy
from .proxy_provider import ProxyProvider

if TYPE_CHECKING:
    from .algorithms import Algorithm

# Why: these are raised before the request leaves, so resending cannot repeat a side effect
_NEVER_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError)
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Errors a bad proxy can cause. Others (a malformed URL, the local pool being full,
# an undecodable body) are not the proxy's fault and are raised without blaming it.
_PROXY_FAULTS = (
    httpx.NetworkError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ProxyError,
    httpx.RemoteProtocolError,
)

# 407 Proxy Authentication Required can only come from the proxy, never the target
_ALWAYS_PROXY_FAILURE_STATUSES = frozenset({407})


class _Rotation:
    """What the sync and async transports share: settings and the retry decision."""

    def __init__(
        self,
        provider: ProxyProvider,
        algorithm: Optional["Algorithm"] = None,
        max_retries: int = 2,
        retry_statuses: Collection[int] = (),
        **transport_options: Any,
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be 0 or more")
        self.provider = provider
        self.algorithm = algorithm
        self.max_retries = max_retries
        self.retry_statuses = frozenset(retry_statuses) | _ALWAYS_PROXY_FAILURE_STATUSES
        self.last_proxy: Optional[Proxy] = None
        """The proxy used for the most recent request, whether it succeeded or not."""
        self._transport_options = transport_options
        self._lock = threading.Lock()

    def _attempts(self, request: httpx.Request) -> int:
        # A streamed body has been consumed after the first attempt and cannot be resent
        replayable = isinstance(request.stream, httpx.ByteStream)
        return self.max_retries + 1 if replayable else 1

    @staticmethod
    def _may_resend(error: Exception, request: httpx.Request) -> bool:
        return isinstance(error, _NEVER_SENT) or request.method in _IDEMPOTENT_METHODS

    @staticmethod
    def _key(proxy: Proxy) -> Tuple[str, int, str, str]:
        return (proxy.scheme, proxy.port, proxy.proxy_address, proxy.username)


class RotatingTransport(_Rotation, httpx.BaseTransport):
    """An httpx transport that routes each request through a proxy from a provider.

    Every request asks the provider for a proxy. If the request fails to get through,
    the proxy is reported with
    :meth:`~proxyproviders.proxy_provider.ProxyProvider.report_failure` and the request
    is sent again through the next one, up to ``max_retries`` more times.

    What counts as a failed proxy:

    * a connect error, connect timeout or proxy error: retried for any HTTP method,
      because the request never reached the target
    * a read or write error or timeout, or a broken response: retried for ``GET``,
      ``HEAD`` and ``OPTIONS`` only
    * a ``407 Proxy Authentication Required`` response, or any status you list in
      ``retry_statuses``: retried for any method

    Anything else is returned or raised exactly as httpx would. httpx reports a failed
    TLS handshake with the target as a connect error, so that also counts against the
    proxy. Requests with a streamed or multipart body are sent once and not retried. One connection pool is kept per proxy used, so connections are
    reused when a proxy comes round again.

    :param provider: Where proxies come from
    :param algorithm: Selection algorithm, as for ``provider.get_proxy()``
    :param max_retries: How many more proxies to try after the first one fails
    :param retry_statuses: Extra response status codes treated as a failed proxy, e.g.
        ``{403, 429}``. 407 is always included.
    :param transport_options: Passed to each underlying ``httpx.HTTPTransport``, e.g.
        ``verify=`` or ``http2=True``

    Example:

    .. code-block:: python

        import httpx
        from proxyproviders import Webshare
        from proxyproviders.httpx_transport import RotatingTransport

        transport = RotatingTransport(Webshare(api_key="your-api-key"), max_retries=3)

        with httpx.Client(transport=transport) as client:
            response = client.get("https://httpbin.org/ip")
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._transports: Dict[Tuple[str, int, str, str], httpx.HTTPTransport] = {}

    def _transport_for(self, proxy: Proxy) -> httpx.HTTPTransport:
        with self._lock:
            key = self._key(proxy)
            if key not in self._transports:
                self._transports[key] = httpx.HTTPTransport(
                    proxy=proxy.to_url(), **self._transport_options
                )
            return self._transports[key]

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Send the request through a proxy, moving to the next proxy if it fails."""
        attempts = self._attempts(request)
        for attempt in range(attempts):
            is_last = attempt == attempts - 1
            proxy = self.provider.get_proxy(self.algorithm)
            self.last_proxy = proxy

            try:
                response = self._transport_for(proxy).handle_request(request)
            except _PROXY_FAULTS as error:
                self.provider.report_failure(proxy)
                if is_last or not self._may_resend(error, request):
                    raise
                continue

            if response.status_code in self.retry_statuses:
                self.provider.report_failure(proxy)
                if is_last:
                    return response
                response.close()
                continue

            self.provider.report_success(proxy)
            return response

        raise AssertionError(
            "unreachable: the loop returns or raises"
        )  # pragma: no cover

    def close(self) -> None:
        with self._lock:
            transports = list(self._transports.values())
            self._transports.clear()
        for transport in transports:
            transport.close()


class AsyncRotatingTransport(_Rotation, httpx.AsyncBaseTransport):
    """The async version of :class:`RotatingTransport`, for ``httpx.AsyncClient``.

    It behaves the same way and takes the same arguments. Asking the provider for a
    proxy runs in a worker thread, so a provider refreshing its list from the vendor's
    API does not block the event loop.

    Example:

    .. code-block:: python

        import httpx
        from proxyproviders import Webshare
        from proxyproviders.httpx_transport import AsyncRotatingTransport

        transport = AsyncRotatingTransport(Webshare(api_key="your-api-key"))

        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get("https://httpbin.org/ip")
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._transports: Dict[Tuple[str, int, str, str], httpx.AsyncHTTPTransport] = {}

    def _transport_for(self, proxy: Proxy) -> httpx.AsyncHTTPTransport:
        with self._lock:
            key = self._key(proxy)
            if key not in self._transports:
                self._transports[key] = httpx.AsyncHTTPTransport(
                    proxy=proxy.to_url(), **self._transport_options
                )
            return self._transports[key]

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Send the request through a proxy, moving to the next proxy if it fails."""
        attempts = self._attempts(request)
        for attempt in range(attempts):
            is_last = attempt == attempts - 1
            proxy = await anyio.to_thread.run_sync(
                self.provider.get_proxy, self.algorithm
            )
            self.last_proxy = proxy

            try:
                response = await self._transport_for(proxy).handle_async_request(
                    request
                )
            except _PROXY_FAULTS as error:
                self.provider.report_failure(proxy)
                if is_last or not self._may_resend(error, request):
                    raise
                continue

            if response.status_code in self.retry_statuses:
                self.provider.report_failure(proxy)
                if is_last:
                    return response
                await response.aclose()
                continue

            self.provider.report_success(proxy)
            return response

        raise AssertionError(
            "unreachable: the loop returns or raises"
        )  # pragma: no cover

    async def aclose(self) -> None:
        with self._lock:
            transports = list(self._transports.values())
            self._transports.clear()
        for transport in transports:
            await transport.aclose()
