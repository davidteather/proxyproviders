import secrets
from typing import List, Optional

from ..models.proxy import Proxy
from ..proxy_provider import ProxyConfig, ProxyProvider


class NodeMaven(ProxyProvider):
    """NodeMaven is a proxy provider that offers residential and mobile proxies through one gateway.

    NodeMaven has no list of proxies to fetch: every proxy is the same gateway, and the
    username selects the exit. A sticky session id in the username keeps one exit IP for
    that session, so this provider creates ``sessions`` proxies with distinct session ids.
    Targeting (country, region, city, ISP) also goes in the username, through
    ``username_suffix``. Docs: `<https://nodemaven.com>`_

    No API call is made; the proxies are built from your proxy username and password,
    which you can find in the NodeMaven dashboard.

    :param username: Your NodeMaven proxy username
    :param password: Your NodeMaven proxy password
    :param sessions: How many sticky sessions to create, each with its own exit IP. With 0 a
        single proxy without a session id is returned, and the exit can change per connection.
    :param username_suffix: Optional targeting appended to the username, e.g. ``"-country-us"``
        or ``"-country-us-region-california"``
    :param ttl: Optional lifetime of each sticky session, e.g. ``"30m"`` or ``"2h"``
    :param protocol: ``"http"`` (port 8080) or ``"socks5"`` (port 1080)
    :param config: Configuration for the proxy provider. View the ProxyConfig class docs for more information.
        Every refresh creates new session ids, so set ``refresh_interval=0`` to keep the same exits.

    Example:

    .. code-block:: python

        from proxyproviders import NodeMaven, ProxyConfig

        # 10 sticky US sessions, kept until you refresh
        proxy_provider = NodeMaven(
            username="your-username",
            password="your-password",
            sessions=10,
            username_suffix="-country-us",
            config=ProxyConfig(refresh_interval=0),
        )

        proxies = proxy_provider.list_proxies()  # 10 proxies, one exit IP each
    """

    _GATEWAY = "gate.nodemaven.com"
    _PORTS = {"http": 8080, "socks5": 1080}
    _PROTOCOLS = {"http": ["http", "https"], "socks5": ["socks5"]}

    def __init__(
        self,
        username: str,
        password: str,
        sessions: int = 1,
        username_suffix: Optional[str] = None,
        ttl: Optional[str] = None,
        protocol: str = "http",
        config: Optional[ProxyConfig] = None,
    ):
        super().__init__(config)
        if not username or not password:
            raise ValueError("NodeMaven needs both a username and a password")
        if sessions < 0:
            raise ValueError("sessions must be 0 or more")
        if protocol not in self._PORTS:
            raise ValueError(
                f"Unsupported protocol '{protocol}', use one of {sorted(self._PORTS)}"
            )
        if username_suffix and "-sid-" in username_suffix:
            raise ValueError(
                "username_suffix must not carry a session id, this provider adds one per session"
            )
        self.username = username
        self.password = password
        self.sessions = sessions
        self.username_suffix = username_suffix or ""
        self.ttl = ttl
        self.protocol = protocol

    def _fetch_proxies(self) -> List[Proxy]:
        base = self.username + self.username_suffix
        if self.sessions == 0:
            return [self._proxy("rotating", base)]

        proxies = []
        for _ in range(self.sessions):
            # Hex ids, so a session id never contains the '-' the gateway splits on
            session_id = secrets.token_hex(6)
            username = f"{base}-sid-{session_id}"
            if self.ttl:
                username += f"-ttl-{self.ttl}"
            proxies.append(self._proxy(session_id, username))
        return proxies

    def _proxy(self, proxy_id: str, username: str) -> Proxy:
        return Proxy(
            id=proxy_id,
            username=username,
            password=self.password,
            proxy_address=self._GATEWAY,
            port=self._PORTS[self.protocol],
            protocols=list(self._PROTOCOLS[self.protocol]),
        )
