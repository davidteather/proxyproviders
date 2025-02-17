import requests
from datetime import datetime
from typing import List, Dict, Optional
from ..proxy_provider import ProxyProvider
from ..errors import ProxyFetchError, ProxyConversionError, ProxyInvalidResponseError
from ..models.proxy import Proxy

class Webshare(ProxyProvider):
    """Webshare API client for fetching proxies.
    
    Webshare is a proxy provider that offers residential and datacenter proxies.

    Create an account [here](https://www.webshare.io/?referral_code=3x5812idzzzp) (affiliate link) to get started with 10 free data center proxies.
    """
    BASE_URL = "https://proxy.webshare.io/api/v2"
    PROTOCOLS = ["http", "https"]

    def __init__(self, api_key: str, search_params: Optional[dict] = None):
        """
        Initialize the Webshare API client with an API key and optional parameters.

        :param api_key: Your Webshare API key
        :param params: Optional parameters to include in the API requests

        Example:
        ```
        ws = Webshare(api_key="your-api-key", params={"country_code_in": "US"})
        ```

        You can find your API key in the Webshare dashboard [here](https://dashboard.webshare.io/userapi/keys)

        You can find a list of all available parameters in the Webshare API documentation [here](https://apidocs.webshare.io/proxy-list/list#parameters)
        """
        self.api_key = api_key
        self.search_params = search_params or {}
        self.proxies: List[Proxy] = None

    def fetch_proxies(self) -> List[Proxy]:
        """Fetches proxies from Webshare API and converts them to the standardized Proxy format."""
        headers = {"Authorization": f"Token {self.api_key}"}

        all_proxies = []
        page = 1
        
        while True:
            default_params = {
                "mode": "direct",
                "page": page,
                "page_size": 100,
            }

            params = {**default_params, **self.search_params}

            try:
                response = requests.get(f"{self.BASE_URL}/proxy/list", params=params, headers=headers)
                response.raise_for_status()  # Raises HTTPError for bad responses
            except requests.exceptions.RequestException as e:
                raise ProxyFetchError(f"Failed to fetch proxies: {str(e)}") from e

            data = response.json()

            proxy_data = data.get("results")
            if not proxy_data:
                raise ProxyInvalidResponseError(response.text)
                
            all_proxies.extend([self._convert_to_proxy(proxy) for proxy in proxy_data])

            if data.get("next") is None: # no more pages
                break

        self.proxies = all_proxies
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
                protocols=self.PROTOCOLS,
            )
        except (KeyError, ValueError) as e:
            raise ProxyConversionError(f"Failed to convert proxy data: {str(e)}") from e

    def _parse_timestamp(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parses an ISO 8601 timestamp string into a datetime object."""
        if timestamp:
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                return None
        return None