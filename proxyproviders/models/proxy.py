from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Proxy:
    """Our shared data model for a proxy object across all providers."""
    
    id: str
    """A unique identifier for the proxy"""
    
    username: str
    """The username required for authenticating with the proxy"""
    
    password: str
    """The password required for authenticating with the proxy"""
    
    proxy_address: str
    """The IP address or domain name of the proxy"""
    
    port: int
    """The port number through which the proxy connection is established"""
    
    country_code: Optional[str] = None
    """The country code where the proxy is located, e.g., 'US', 'FR'. Optional"""
    
    city_name: Optional[str] = None
    """The city name where the proxy is located, e.g., 'New York', 'Paris'. Optional"""
    
    created_at: Optional[datetime] = None
    """The timestamp when the proxy was created. Optional"""
    
    protocols: List[str] = None
    """A list of connection protocols supported by the proxy, e.g., ['http', 'https']"""
