from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Proxy:
    """
    A class representing a proxy with authentication details and connection properties.

    Attributes:
        id (str): A unique identifier for the proxy.
        username (str): The username required for authenticating with the proxy.
        password (str): The password required for authenticating with the proxy.
        proxy_address (str): The IP address or domain name of the proxy.
        port (int): The port number through which the proxy connection is established.
        country_code (Optional[str]): The country code where the proxy is located, e.g., 'US', 'FR'. Optional.
        city_name (Optional[str]): The city name where the proxy is located, e.g., 'New York', 'Paris'. Optional.
        created_at (Optional[datetime]): The timestamp when the proxy was created. Optional.
        protocols (List[str]): A list of connection protocols supported by the proxy, e.g., ['http', 'https'].

    Example:
        proxy = Proxy(
            id="12345",
            username="user1",
            password="securepass",
            proxy_address="192.168.1.1",
            port=8080,
            country_code="US",
            city_name="New York",
            created_at=datetime(2023, 1, 1, 12, 0),
            protocols=["http", "https"]
        )
    """
    id: str
    username: str
    password: str
    proxy_address: str
    port: int
    country_code: Optional[str]
    city_name: Optional[str]
    created_at: Optional[datetime]
    protocols: List[str]
