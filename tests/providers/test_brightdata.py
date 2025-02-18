import pytest
import responses

from proxyproviders.exceptions import (
    ProxyFetchException,
    ProxyInvalidResponseException,
)

@responses.activate
def test_fetch_proxies_super_proxy(brightdata_provider):
    """
    Unit test: Test _fetch_proxies in super proxy mode.
    In this mode, BrightData returns a single proxy based on get_zone_username and get_zone_passwords.
    """
    # Ensure super proxy mode is enabled (default)
    brightdata_provider.use_super_proxy = True

    # Simulate /status endpoint call used in get_zone_username.
    responses.add(
        responses.GET,
        "https://api.brightdata.com/status",
        json={"customer": "customer123"},
        status=200,
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    # Simulate /zone/passwords endpoint call used in get_zone_passwords.
    responses.add(
        responses.GET,
        "https://api.brightdata.com/zone/passwords",
        json={"passwords": ["pass123"]},
        status=200,
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    proxies = brightdata_provider._fetch_proxies()
    assert isinstance(proxies, list)
    assert len(proxies) == 1

    proxy = proxies[0]
    expected_username = "brd-customer-customer123-zone-test-zone"
    assert proxy.username == expected_username
    assert proxy.password == "pass123"
    assert proxy.proxy_address == brightdata_provider._SUPER_PROXY_ADDRESS
    assert proxy.port == brightdata_provider._SUPER_PROXY_PORT


@responses.activate
def test_fetch_proxies_ip_mode(brightdata_provider):
    """
    Unit test: Test _fetch_proxies in non-super-proxy (IP) mode.
    In this mode, BrightData calls list_all_ips_in_zone to create a proxy for each IP.
    """
    # Switch to IP mode
    brightdata_provider.use_super_proxy = False

    # Simulate /status endpoint call for username
    responses.add(
        responses.GET,
        "https://api.brightdata.com/status",
        json={"customer": "customer456"},
        status=200,
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    # Simulate /zone/passwords endpoint call for passwords.
    responses.add(
        responses.GET,
        "https://api.brightdata.com/zone/passwords",
        json={"passwords": ["pass456"]},
        status=200,
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    # Simulate /zone/route_ips endpoint call for list_all_ips_in_zone.
    responses.add(
        responses.GET,
        "https://api.brightdata.com/zone/route_ips",
        json=[
            {"ip": "192.168.0.1", "country": "US"},
            {"ip": "192.168.0.2", "country": "CA"},
        ],
        status=200,
        # Note: When matching query parameters, string values are used.
        match=[responses.matchers.query_param_matcher({
            "zone": "test-zone",
            "list_countries": "True"
        })],
    )

    proxies = brightdata_provider._fetch_proxies()
    assert isinstance(proxies, list)
    assert len(proxies) == 2

    # Verify the proxy for the first IP.
    expected_username1 = "brd-customer-customer456-zone-test-zone-ip-192.168.0.1"
    assert proxies[0].username == expected_username1
    assert proxies[0].password == "pass456"
    assert proxies[0].proxy_address == brightdata_provider._SUPER_PROXY_ADDRESS
    assert proxies[0].country_code == "US"

    # Verify the proxy for the second IP.
    expected_username2 = "brd-customer-customer456-zone-test-zone-ip-192.168.0.2"
    assert proxies[1].username == expected_username2
    assert proxies[1].country_code == "CA"


@responses.activate
def test_get_zone_username_failure(brightdata_provider):
    """
    Unit test: Test that get_zone_username raises an exception when no customer data is returned.
    """
    # Simulate /status endpoint call without 'customer'
    responses.add(
        responses.GET,
        "https://api.brightdata.com/status",
        json={},  # Missing 'customer'
        status=200,
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    with pytest.raises(ProxyInvalidResponseException):
        brightdata_provider.get_zone_username("test-zone")


@responses.activate
def test_get_zone_passwords_failure(brightdata_provider):
    """
    Unit test: Test that get_zone_passwords raises an exception on an error status.
    """
    # Simulate error on /zone/passwords endpoint.
    responses.add(
        responses.GET,
        "https://api.brightdata.com/zone/passwords",
        json={"error": "Invalid zone"},
        status=403,
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    with pytest.raises(ProxyFetchException):
        brightdata_provider.get_zone_passwords("test-zone")


@responses.activate
def test_list_all_ips_in_zone_failure(brightdata_provider):
    """
    Unit test: Test that list_all_ips_in_zone raises an exception on an error status.
    """
    responses.add(
        responses.GET,
        "https://api.brightdata.com/zone/route_ips",
        json={"error": "Not found"},
        status=404,
        match=[responses.matchers.query_param_matcher({
            "zone": "test-zone",
            "list_countries": "True"
        })],
    )

    with pytest.raises(ProxyFetchException):
        brightdata_provider.list_all_ips_in_zone("test-zone")


@responses.activate
def test_make_request_invalid_json(brightdata_provider):
    """
    Unit test: Test that _make_request raises an exception when the response contains invalid JSON.
    """
    # Simulate an endpoint (e.g. /status) returning invalid JSON.
    responses.add(
        responses.GET,
        "https://api.brightdata.com/status",
        body="Not a JSON response",
        status=200,
        content_type="application/json",
        match=[responses.matchers.query_param_matcher({"zone": "test-zone"})],
    )

    with pytest.raises(ProxyInvalidResponseException):
        brightdata_provider.get_zone_username("test-zone")
