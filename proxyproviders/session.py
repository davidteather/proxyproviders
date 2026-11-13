"""An opt-in ``requests.Session`` that picks a proxy for every request.

Nothing else in the package uses this module. Import it when you want rotation and
retries handled for you instead of calling ``provider.get_proxy()`` yourself.
"""

import inspect
import threading
from typing import TYPE_CHECKING, Any, Callable, Collection, Dict, Optional, Union

import requests
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError

from .models.proxy import Proxy, ProxyFormat
from .proxy_provider import ProxyProvider

if TYPE_CHECKING:
    from .algorithms import Algorithm

# Why: a dropped connection may mean the server already acted, so only these are resent
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# 407 Proxy Authentication Required can only come from the proxy, never the target
_ALWAYS_PROXY_FAILURE_STATUSES = frozenset({407})

_REQUEST_SIGNATURE = inspect.signature(requests.Session.request)


def _never_sent(error: BaseException) -> bool:
    """Whether a failed request is known not to have reached the target.

    True only when the failure was in connecting to the proxy, or in opening the tunnel
    through it. ``requests`` also raises ``ProxyError`` when a proxy drops the connection
    *after* relaying the request, so the exception type alone does not answer this.
    """
    # Why: __context__ is not followed, it holds whatever the *caller* was handling
    seen = set()
    pending = [error]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))

        if isinstance(current, (NewConnectionError, ConnectTimeoutError)):
            return True
        if isinstance(current, requests.exceptions.ConnectTimeout):
            return True
        if isinstance(current, OSError) and "Tunnel connection failed" in str(current):
            return True

        linked = [
            getattr(current, "reason", None),
            getattr(current, "original_error", None),
            current.__cause__,
            *current.args,
        ]
        pending.extend(item for item in linked if isinstance(item, BaseException))
    return False


class RotatingSession(requests.Session):
    """A ``requests.Session`` that routes each request through a proxy from a provider.

    Every request asks the provider for a proxy. If the request fails to get through the
    proxy, the proxy is reported with
    :meth:`~proxyproviders.proxy_provider.ProxyProvider.report_failure` and the request
    is tried again on the next one, up to ``max_retries`` more times. It works with any
    provider, including :class:`~proxyproviders.providers.proxy_list.ProxyList`.

    What counts as a failed proxy, and when the request is sent again:

    * Failing to connect to the proxy, or to open a tunnel through it: retried for any
      HTTP method, because the request never reached the target.
    * Any other connection error or timeout, such as a proxy that drops the connection
      or stops responding: retried for ``GET``, ``HEAD`` and ``OPTIONS`` only. Other
      methods may already have been acted on, so the error is raised instead.
    * A ``407 Proxy Authentication Required`` response, or any status you list in
      ``retry_statuses``: retried for any method.

    Anything else, including ordinary error statuses such as 404 or 500, is returned or
    raised exactly as ``requests`` would. A TLS error is raised without blaming the
    proxy, since it usually comes from the target. A slow target cannot be told apart
    from a slow proxy, so a read timeout counts against the proxy. Deciding that a
    response means "banned" is left to you: list statuses in ``retry_statuses`` or call
    ``report_failure`` yourself.

    A request made with an explicit ``proxies=`` argument is sent as given, with no
    rotation. Requests that upload files or stream their body are sent once and never
    retried, since the body cannot be read twice.

    :param provider: Where proxies come from
    :param algorithm: Selection algorithm, as for ``provider.get_proxy()``. Defaults to the
        provider's round robin.
    :param max_retries: How many more proxies to try after the first one fails
    :param retry_statuses: Extra response status codes treated as a failed proxy, e.g.
        ``{403, 429}`` for a target that blocks proxies. 407 is always included.

    Example:

    .. code-block:: python

        from proxyproviders import Webshare
        from proxyproviders.session import RotatingSession

        session = RotatingSession(Webshare(api_key="your-api-key"), max_retries=3)

        response = session.get("https://httpbin.org/ip", timeout=10)
        print(response.json(), session.last_proxy)
    """

    def __init__(
        self,
        provider: ProxyProvider,
        algorithm: Optional["Algorithm"] = None,
        max_retries: int = 2,
        retry_statuses: Collection[int] = (),
    ):
        super().__init__()
        if max_retries < 0:
            raise ValueError("max_retries must be 0 or more")
        self.provider = provider
        self.algorithm = algorithm
        self.max_retries = max_retries
        self.retry_statuses = frozenset(retry_statuses) | _ALWAYS_PROXY_FAILURE_STATUSES
        self.last_proxy: Optional[Proxy] = None
        """The proxy used for the most recent request, whether it succeeded or not."""
        self._local = threading.local()

    def request(
        self,
        method: Union[str, bytes],
        url: Union[str, bytes],
        *args: Any,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a request through a proxy from the provider, retrying on the next proxy
        if this one fails. Takes the same arguments as ``requests.Session.request``."""
        bound = _REQUEST_SIGNATURE.bind(self, method, url, *args, **kwargs)
        options = dict(bound.arguments)
        for name in ("self", "method", "url"):
            options.pop(name)

        if options.get("proxies"):
            return requests.Session.request(self, method, url, **options)

        method_name = (
            method.decode() if isinstance(method, bytes) else str(method)
        ).upper()

        def attempt(proxies: Dict[str, str]) -> requests.Response:
            return requests.Session.request(
                self, method, url, **{**options, "proxies": proxies}
            )

        return self._rotate(method_name, self._replayable(options), attempt)

    def send(
        self, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        """Send a prepared request. Rotates like :meth:`request` unless ``proxies`` is given."""
        if getattr(self._local, "rotating", False) or kwargs.get("proxies"):
            return super().send(request, **kwargs)

        def attempt(proxies: Dict[str, str]) -> requests.Response:
            return requests.Session.send(
                self, request, **{**kwargs, "proxies": proxies}
            )

        replayable = request.body is None or isinstance(request.body, (str, bytes))
        return self._rotate((request.method or "GET").upper(), replayable, attempt)

    def _rotate(
        self,
        method_name: str,
        replayable: bool,
        attempt: Callable[[Dict[str, str]], requests.Response],
    ) -> requests.Response:
        attempts = self.max_retries + 1 if replayable else 1

        for number in range(attempts):
            is_last = number == attempts - 1
            proxy = self.provider.get_proxy(self.algorithm)
            self.last_proxy = proxy

            # Marks the nested send() calls that requests makes as already handled here
            was_rotating = getattr(self._local, "rotating", False)
            self._local.rotating = True
            try:
                response = attempt(proxy.format(ProxyFormat.REQUESTS))
            except requests.exceptions.SSLError:
                raise
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as error:
                self.provider.report_failure(proxy)
                safe_to_resend = (
                    _never_sent(error) or method_name in _IDEMPOTENT_METHODS
                )
                if is_last or not safe_to_resend:
                    raise
                continue
            finally:
                self._local.rotating = was_rotating

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

    @staticmethod
    def _replayable(options: Dict[str, Any]) -> bool:
        """Whether the request body can be sent a second time."""
        if options.get("files"):
            # File objects are read to the end on the first attempt
            return False
        body = options.get("data")
        return body is None or isinstance(body, (str, bytes, dict, list, tuple))
