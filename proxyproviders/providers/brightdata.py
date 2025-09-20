from typing import Dict, List, Optional

import requests

from ..exceptions import ProxyFetchException, ProxyInvalidResponseException
from ..models.proxy import Proxy
from ..proxy_provider import ProxyConfig, ProxyProvider


class BrightData(ProxyProvider):
    """BrightData (formerly luminati) is a proxy provider that offers residential and datacenter proxies.

    Create an account `here <https://get.brightdata.com/davidteather>`_ (affiliate link).

    You can find your API key in the account settings `here <https://brightdata.com/cp/setting/users>`_ then create "add token" with scope "limit" (`BrightData article <https://docs.brightdata.com/general/account/api-token>`_ for more info)

    The BrightData API documentation is `here <https://docs.brightdata.com/api-reference/account-management-api/Get_active_Zones?playground=open>`_

    :param api_key: Your BrightData API key
    :param zone: The zone ID/name to fetch proxies for (you can get this from the BrightData dashboard)
    :param username_suffix: Optional suffix to append to the username `more info <https://docs.brightdata.com/proxy-networks/config-options>`_ allows you to target region, city, etc. (requires use_super_proxy=True)
    :param use_super_proxy: Optional flag to use super proxy instead of targeting specific IPs, this is enabled by default. If you want to target specific IPs or have consistent IPs for a session, set this to False.
    :param config: Configuration for the proxy provider. View the ProxyConfig class docs for more information.

    Example:

    .. code-block:: python

        from proxyproviders import BrightData

        # Initialize the BrightData API client with an API key and a zone
        proxy_provider = BrightData(api_key="your-api-key", zone="my_zone")

        # Fetch proxies
        proxies = proxy_provider.list_proxies() # returns one proxy for super proxy by default

        # If you want to manage specific IPs
        proxy_provider = BrightData(api_key="your-api-key", zone="my_zone", use_super_proxy=False)
        proxies = proxy_provider.list_proxies() # returns multiple proxies for each IP in the zone (potentially thousands)
    """

    _BASE_URL = "https://api.brightdata.com"
    _SUPER_PROXY_ADDRESS = "brd.superproxy.io"
    _SUPER_PROXY_PORT = 33335
    _PROTOCOLS: List[str] = ["http", "https"]  # BrightData supports both HTTP and HTTPS

    def __init__(
        self,
        api_key: str,
        zone: str,
        username_suffix: Optional[str] = None,
        use_super_proxy: Optional[bool] = True,
        config: Optional[ProxyConfig] = None,
    ):
        super().__init__(config)
        self.api_key = api_key
        self.zone = zone
        self.username_suffix = username_suffix
        self.use_super_proxy = use_super_proxy

    def _fetch_proxies(self) -> List[Proxy]:
        username = self.get_zone_username(self.zone)
        if self.username_suffix:
            username += self.username_suffix

        passwords = self.get_zone_passwords(self.zone)

        if self.use_super_proxy:
            # Let the super proxy handle the IP rotation
            return [
                Proxy(
                    id="super",
                    username=username,
                    password=passwords["passwords"][0],
                    proxy_address=self._SUPER_PROXY_ADDRESS,
                    port=self._SUPER_PROXY_PORT,
                    protocols=self._PROTOCOLS,
                )
            ]

        proxies = []

        # Fetch all IPs in the zone, and create a proxy for each
        # Brightdata doesn't let us target directly so we tell the superproxy what to do
        ips = self.list_all_ips_in_zone(self.zone)

        for ip in ips:
            ip_targeted_username = username + f"-ip-{ip['ip']}"

            proxies.append(
                Proxy(
                    id=ip["ip"],
                    username=ip_targeted_username,
                    password=passwords["passwords"][0],
                    proxy_address=self._SUPER_PROXY_ADDRESS,
                    port=self._SUPER_PROXY_PORT,
                    country_code=ip["country"],
                    protocols=self._PROTOCOLS,
                )
            )

        return proxies

    def get_active_zones(self) -> Dict:
        """Fetches active zones from BrightData API.

        Response:

        .. code-block:: json

            [
                {
                    "name": "zone1",
                    "type": "dc",
                }
            ]

        """
        return self._make_request("/zone/get_active_zones", "GET")

    def get_zone_username(self, zone: str) -> str:
        """Fetches zone username for the given zone ID from BrightData API.

        Note: this isn't directly an API endpoint, I'm sort of reconstructing some things here and it seems to behave a little weird.

        :param zone: The zone ID to fetch username for
        """

        data = self._make_request(f"/status", "GET", params={"zone": zone})

        customer = data.get("customer")
        if not customer:
            raise ProxyInvalidResponseException("Failed to fetch customer data")

        return f"brd-customer-{customer}-zone-{zone}"

    def get_zone_passwords(self, zone: str) -> Dict:
        """Fetches zone passwords from BrightData API.

        :param zone: The zone ID to fetch passwords for

        Response:


        .. code-block:: json

            {
                "passwords": [
                    "password1",
                    "password2",
                ]
            }

        """
        return self._make_request(f"/zone/passwords", "GET", params={"zone": zone})

    def list_all_ips_in_zone(self, zone: str, country: Optional[str] = None) -> Dict:
        """Fetches all IPs in a zone from BrightData API.

        :param zone: The zone ID to fetch IPs for
        :param country: Optional 2-letter country code to filter IPs by

        Response:


        .. code-block:: json

            [
                {
                    "ip": "192.168.1.1",
                    "country": "US",
                }
            ]

        """
        return self._make_request(
            f"/zone/route_ips",
            "GET",
            params={"zone": zone, "list_countries": True, "country": country},
        )

    def _make_request(
        self,
        path: str,
        method: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Dict:
        """Makes a request to the BrightData API.

        :param path: The path to the endpoint
        :param method: The HTTP method to use
        :param params: Optional parameters to include in the request
        :param json: Optional JSON data to include in the request
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{self._BASE_URL}{path}"
        response = requests.request(
            method, url, headers=headers, params=params, json=json
        )

        if response.status_code != 200:
            raise ProxyFetchException(
                f"Failed to fetch from BrightData, got status code {response.status_code}, text: {response.text}"
            )

        try:
            data = response.json()
        except Exception as e:
            raise ProxyInvalidResponseException(
                f"Failed to parse response: {str(e)}"
            ) from e

        return data
