from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from .models.proxy import Proxy

class ProxyProvider(ABC):
    def __init__(self, api_key: str, search_params: Optional[dict] = None):
        self.api_key = api_key
        self.search_params = search_params or {}
        self.proxies: List[Proxy] = None

    @abstractmethod
    def fetch_proxies(self) -> None:
        """Fetch proxies from the provider and store them in self.proxies."""
        pass

    def list_proxies(self, format: Optional[Callable[[Proxy], Proxy]] = None) -> List[Proxy]:
        """
        Returns the stored proxies.  
        If a format function is provided, it applies that function to each proxy.
        """
        if not self.proxies:
            self.fetch_proxies()

        if format:
            return [format(proxy) for proxy in self.proxies]
        return self.proxies