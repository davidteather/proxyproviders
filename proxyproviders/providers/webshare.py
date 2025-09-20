from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..exceptions import (
    ProxyConversionException,
    ProxyFetchException,
    ProxyInvalidResponseException,
)
from ..models.proxy import Proxy
from ..proxy_provider import ProxyConfig, ProxyProvider


class Webshare(ProxyProvider):
    """Webshare is a proxy provider that offers residential and datacenter proxies.

    Create an account for webshare `here <https://www.webshare.io/?referral_code=3x5812idzzzp>`_ (affiliate link) to get started with 10 free data center proxies.

    You can find your API key in the Webshare dashboard `here <https://dashboard.webshare.io/userapi/keys>`_

    You can find a list of all available parameters in the Webshare API documentation `here <https://apidocs.webshare.io/proxy-list/list#parameters>`_

    :param api_key: Your Webshare API key
    :param search_params: Optional parameters to include in the API requests
    :param config: Configuration for the proxy provider. View the ProxyConfig class docs for more information.

    Example:

    .. code-block:: python

        from proxyproviders import Webshare

        # Initialize the Webshare API client with an API key and optional parameters
        proxy_provider = Webshare(api_key="your-api-key", params={"country_code_in": "US"})

        # Fetch proxies
        proxies = proxy_provider.list_proxies()

        # With config
        from proxyproviders import ProxyConfig

        config = ProxyConfig(refresh_interval=60)
        proxy_provider = Webshare(api_key="your-api-key", params={"country_code_in": "US"}, config=config)

        # Fetch proxies
        proxies = proxy_provider.list_proxies()
    """

    _BASE_URL = "https://proxy.webshare.io/api/v2"
    _PROTOCOLS = ["http", "https"]

    def __init__(
        self,
        api_key: str,
        search_params: Optional[dict] = None,
        config: Optional[ProxyConfig] = None,
    ):
        super().__init__(config)
        self.api_key = api_key
        self.search_params = search_params or {}

    def _fetch_proxies(self) -> List[Proxy]:
        """Fetches proxies from Webshare API and converts them to the standardized Proxy format."""
        headers = {"Authorization": f"Token {self.api_key}"}

        all_proxies = []
        page = 0

        while True:
            page += 1
            default_params = {
                "mode": "direct",
                "page": page,
                "page_size": 100,
            }

            params = {**default_params, **self.search_params}
            try:
                response = requests.get(
                    f"{self._BASE_URL}/proxy/list", params=params, headers=headers
                )
                response.raise_for_status()  # Raises HTTPError for bad responses
            except requests.exceptions.RequestException as e:
                raise ProxyFetchException(f"Failed to fetch proxies: {str(e)}") from e

            data = response.json()

            proxy_data = data.get("results")
            if proxy_data is None:
                raise ProxyInvalidResponseException(response.text)

            all_proxies.extend([self._convert_to_proxy(proxy) for proxy in proxy_data])

            if data.get("next") is None:  # no more pages
                break

        return all_proxies

    def _convert_to_proxy(self, data: Dict) -> Proxy:
        """Converts Webshare's proxy data to the shared Proxy format."""
        try:
            return Proxy(
                id=data["id"],
                username=data["username"],
                password=data["password"],
                proxy_address=data["proxy_address"],
                port=int(data["port"]),
                country_code=data.get("country_code"),
                city_name=data.get("city_name"),
                created_at=self._parse_timestamp(data.get("created_at")),
                protocols=self._PROTOCOLS,
            )
        except (KeyError, ValueError) as e:
            raise ProxyConversionException(
                f"Failed to convert proxy data: {str(e)}"
            ) from e

    def _parse_timestamp(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parses an ISO 8601 timestamp string into a datetime object."""
        if timestamp:
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                return None
        return None
