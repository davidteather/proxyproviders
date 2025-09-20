"""Selection algorithms for choosing proxies from a provider."""

import random
import threading
from abc import ABC, abstractmethod
from typing import Dict, List

from .models.proxy import Proxy


class Algorithm(ABC):
    """Base class for proxy selection algorithms.

    Users can extend this class to create custom proxy selection logic.

    Example:
        >>> class MyAlgorithm(Algorithm):
        ...     def select(self, proxies):
        ...         return proxies[0]  # Always return first proxy
        ...
        >>> algorithm = MyAlgorithm()
        >>> proxy = provider.get_proxy(algorithm)
    """

    @abstractmethod
    def select(self, proxies: List[Proxy]) -> Proxy:
        """Select a proxy from the list.

        :param proxies: List of available proxies
        :return: Selected proxy
        :raises ValueError: If proxy list is empty
        """
        pass


class Random(Algorithm):
    """Random proxy selection algorithm.

    Selects a random proxy from the available list on each call.

    Example:
        >>> algorithm = Random()
        >>> proxy = provider.get_proxy(algorithm)
    """

    def select(self, proxies: List[Proxy]) -> Proxy:
        """Select a random proxy from the list.

        :param proxies: List of available proxies
        :return: Randomly selected proxy
        :raises ValueError: If proxy list is empty
        """
        if not proxies:
            raise ValueError("Cannot select from empty proxy list")
        return random.choice(proxies)


class RoundRobin(Algorithm):
    """Round-robin proxy selection algorithm with state tracking.

    Cycles through proxies in order, maintaining state across calls.
    Each RoundRobin instance maintains its own independent state.

    Example:
        >>> algorithm = RoundRobin()
        >>> proxy1 = provider.get_proxy(algorithm)
        >>> proxy2 = provider.get_proxy(algorithm)  # Next proxy in sequence
    """

    def __init__(self):
        """Initialize round-robin algorithm with state tracking."""
        self._current_index = 0
        self._lock = threading.Lock()

    def select(self, proxies: List[Proxy]) -> Proxy:
        """Select next proxy in round-robin sequence.

        :param proxies: List of available proxies
        :return: Next proxy in round-robin sequence
        :raises ValueError: If proxy list is empty
        """
        if not proxies:
            raise ValueError("Cannot select from empty proxy list")

        with self._lock:
            selected_proxy = proxies[self._current_index % len(proxies)]
            self._current_index = (self._current_index + 1) % len(proxies)

        return selected_proxy


class First(Algorithm):
    """First proxy selection algorithm.

    Always selects the first proxy from the list.
    Useful for deterministic behavior or when proxies are pre-sorted.

    Example:
        >>> algorithm = First()
        >>> proxy = provider.get_proxy(algorithm)  # Always first proxy
    """

    def select(self, proxies: List[Proxy]) -> Proxy:
        """Select the first proxy from the list.

        :param proxies: List of available proxies
        :return: First proxy in the list
        :raises ValueError: If proxy list is empty
        """
        if not proxies:
            raise ValueError("Cannot select from empty proxy list")
        return proxies[0]
