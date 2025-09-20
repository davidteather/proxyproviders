"""Tests for the algorithms module."""

from datetime import datetime
from typing import List

import pytest

from proxyproviders.algorithms import Algorithm, First, Random, RoundRobin
from proxyproviders.models.proxy import Proxy
from proxyproviders.proxy_provider import ProxyConfig, ProxyProvider


class MockProxyProvider(ProxyProvider):
    """Mock proxy provider for testing."""

    def __init__(self, proxies: List[Proxy], config: ProxyConfig = None):
        super().__init__(config)
        self._test_proxies = proxies

    def _fetch_proxies(self) -> List[Proxy]:
        return self._test_proxies


@pytest.fixture
def sample_proxies():
    """Sample proxy data for testing."""
    return [
        Proxy(
            id="1",
            username="user1",
            password="pass1",
            proxy_address="192.168.1.1",
            port=8080,
            country_code="US",
            city_name="New York",
            protocols=["http", "https"],
        ),
        Proxy(
            id="2",
            username="user2",
            password="pass2",
            proxy_address="192.168.1.2",
            port=8081,
            country_code="FR",
            city_name="Paris",
            protocols=["http"],
        ),
        Proxy(
            id="3",
            username="user3",
            password="pass3",
            proxy_address="192.168.1.3",
            port=8082,
            country_code="US",
            city_name="Los Angeles",
            protocols=["https"],
        ),
    ]


@pytest.fixture
def empty_proxy_list():
    """Empty proxy list for testing error cases."""
    return []


class TestRandomAlgorithm:
    """Tests for Random algorithm."""

    def test_random_returns_proxy_from_list(self, sample_proxies):
        """Test that Random returns a proxy from the list."""
        algorithm = Random()
        proxy = algorithm.select(sample_proxies)
        assert proxy in sample_proxies

    def test_random_empty_list_raises_error(self, empty_proxy_list):
        """Test that Random raises ValueError for empty list."""
        algorithm = Random()
        with pytest.raises(ValueError, match="Cannot select from empty proxy list"):
            algorithm.select(empty_proxy_list)

    def test_random_single_proxy(self, sample_proxies):
        """Test Random with single proxy."""
        algorithm = Random()
        single_proxy = [sample_proxies[0]]
        proxy = algorithm.select(single_proxy)
        assert proxy == sample_proxies[0]


class TestRoundRobinAlgorithm:
    """Tests for RoundRobin algorithm."""

    def test_round_robin_cycles_through_proxies(self, sample_proxies):
        """Test that RoundRobin cycles through all proxies."""
        algorithm = RoundRobin()
        selected = []

        # Select proxies twice the length of the list
        for _ in range(len(sample_proxies) * 2):
            proxy = algorithm.select(sample_proxies)
            selected.append(proxy)

        # Should cycle through all proxies twice
        assert selected[:3] == sample_proxies
        assert selected[3:6] == sample_proxies

    def test_round_robin_independent_instances(self, sample_proxies):
        """Test that different RoundRobin instances maintain independent state."""
        algorithm1 = RoundRobin()
        algorithm2 = RoundRobin()

        proxy1_alg1 = algorithm1.select(sample_proxies)
        proxy1_alg2 = algorithm2.select(sample_proxies)
        proxy2_alg1 = algorithm1.select(sample_proxies)

        assert proxy1_alg1 == sample_proxies[0]
        assert proxy1_alg2 == sample_proxies[0]  # Different instance, starts over
        assert proxy2_alg1 == sample_proxies[1]  # Same instance, next proxy

    def test_round_robin_empty_list_raises_error(self, empty_proxy_list):
        """Test that RoundRobin raises ValueError for empty list."""
        algorithm = RoundRobin()
        with pytest.raises(ValueError, match="Cannot select from empty proxy list"):
            algorithm.select(empty_proxy_list)

    def test_round_robin_state_persistence(self, sample_proxies):
        """Test that RoundRobin maintains state across calls."""
        algorithm = RoundRobin()

        # Select all proxies once
        selected_first_round = []
        for _ in range(len(sample_proxies)):
            selected_first_round.append(algorithm.select(sample_proxies))

        # Select all proxies again
        selected_second_round = []
        for _ in range(len(sample_proxies)):
            selected_second_round.append(algorithm.select(sample_proxies))

        # Both rounds should be identical and in order
        assert selected_first_round == sample_proxies
        assert selected_second_round == sample_proxies


class TestFirstAlgorithm:
    """Tests for First algorithm."""

    def test_first_returns_first_proxy(self, sample_proxies):
        """Test that First returns the first proxy."""
        algorithm = First()
        proxy = algorithm.select(sample_proxies)
        assert proxy == sample_proxies[0]

    def test_first_always_returns_same_proxy(self, sample_proxies):
        """Test that First always returns the same proxy."""
        algorithm = First()
        proxy1 = algorithm.select(sample_proxies)
        proxy2 = algorithm.select(sample_proxies)
        assert proxy1 == proxy2 == sample_proxies[0]

    def test_first_empty_list_raises_error(self, empty_proxy_list):
        """Test that First raises ValueError for empty list."""
        algorithm = First()
        with pytest.raises(ValueError, match="Cannot select from empty proxy list"):
            algorithm.select(empty_proxy_list)


class TestCustomAlgorithm:
    """Tests for custom algorithm implementation."""

    def test_custom_algorithm_implementation(self, sample_proxies):
        """Test that custom algorithms can be implemented."""

        class LastAlgorithm(Algorithm):
            """Custom algorithm that always selects the last proxy."""

            def select(self, proxies: List[Proxy]) -> Proxy:
                if not proxies:
                    raise ValueError("Cannot select from empty proxy list")
                return proxies[-1]

        algorithm = LastAlgorithm()
        proxy = algorithm.select(sample_proxies)
        assert proxy == sample_proxies[-1]


class TestProxyProviderIntegration:
    """Tests for get_proxy method integration with algorithms."""

    def test_get_proxy_default_algorithm(self, sample_proxies):
        """Test get_proxy with default RoundRobin algorithm."""
        provider = MockProxyProvider(sample_proxies)

        # Should use default RoundRobin
        proxy1 = provider.get_proxy()
        proxy2 = provider.get_proxy()

        assert proxy1 == sample_proxies[0]
        assert proxy2 == sample_proxies[1]

    def test_get_proxy_with_custom_algorithm(self, sample_proxies):
        """Test get_proxy with custom algorithm."""
        provider = MockProxyProvider(sample_proxies)

        proxy = provider.get_proxy(Random())
        assert proxy in sample_proxies

    def test_get_proxy_empty_provider_raises_error(self, empty_proxy_list):
        """Test that get_proxy raises ValueError when provider has no proxies."""
        provider = MockProxyProvider(empty_proxy_list)
        with pytest.raises(ValueError, match="No proxies available from provider"):
            provider.get_proxy()

    def test_get_proxy_with_different_algorithms(self, sample_proxies):
        """Test get_proxy with different algorithm instances."""
        provider = MockProxyProvider(sample_proxies)

        # First should always return first proxy
        first_proxy = provider.get_proxy(First())
        assert first_proxy == sample_proxies[0]

        # Random should return a proxy from the list
        random_proxy = provider.get_proxy(Random())
        assert random_proxy in sample_proxies

        # Default should continue RoundRobin sequence
        default_proxy = provider.get_proxy()
        assert default_proxy == sample_proxies[0]  # First call to default

    def test_default_algorithm_state_persistence(self, sample_proxies):
        """Test that the provider's default algorithm maintains state."""
        provider = MockProxyProvider(sample_proxies)

        # Multiple calls to default should cycle through proxies
        proxies_selected = []
        for _ in range(len(sample_proxies) * 2):
            proxy = provider.get_proxy()
            proxies_selected.append(proxy)

        # Should cycle through all proxies twice
        assert proxies_selected[:3] == sample_proxies
        assert proxies_selected[3:6] == sample_proxies
