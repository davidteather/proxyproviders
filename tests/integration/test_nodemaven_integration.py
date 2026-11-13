import os

import pytest
import requests

from proxyproviders import NodeMaven, ProxyFormat

# Skip integration tests unless explicitly enabled
skip_integration = pytest.mark.skipif(
    not (
        os.getenv("RUN_INTEGRATION_TESTS")
        and os.getenv("NODEMAVEN_USERNAME")
        and os.getenv("NODEMAVEN_PASSWORD")
    ),
    reason="Integration tests require RUN_INTEGRATION_TESTS and NODEMAVEN_USERNAME / NODEMAVEN_PASSWORD",
)


@skip_integration
def test_nodemaven_sticky_session_keeps_its_exit():
    """
    Integration test: send two requests through one sticky session and check that both
    leave from the same exit IP.
    """
    provider = NodeMaven(
        username=os.environ["NODEMAVEN_USERNAME"],
        password=os.environ["NODEMAVEN_PASSWORD"],
        sessions=1,
    )
    proxies = provider.get_proxy().format(ProxyFormat.REQUESTS)

    first = requests.get("https://api.ipify.org", proxies=proxies, timeout=30).text
    second = requests.get("https://api.ipify.org", proxies=proxies, timeout=30).text

    assert first
    assert first == second
