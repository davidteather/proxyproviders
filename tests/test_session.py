"""RotatingSession sends real requests through local proxies, some of them broken."""

import pytest
import requests

from proxyproviders import ProxyList, RotatingSession
from proxyproviders.algorithms import First
from tests.local_servers import BODY, dead_proxy


def session_for(proxies, **kwargs):
    session = RotatingSession(ProxyList(proxies), **kwargs)
    session.trust_env = False
    return session


def test_each_request_uses_the_next_proxy(make_http_proxy, target):
    first, second = make_http_proxy(), make_http_proxy()
    session = session_for([first.proxy(), second.proxy()])

    for _ in range(4):
        assert session.get(target.url, timeout=10).content == BODY

    assert len(first.requests) == len(second.requests) == 2
    assert session.last_proxy.port == second.port


def test_dead_proxy_is_retried_on_a_working_one(http_proxy, target):
    dead = dead_proxy()
    session = session_for([dead, http_proxy.proxy()])

    response = session.get(target.url, timeout=10)

    assert response.content == BODY
    assert http_proxy.requests == [("GET", target.url)]
    assert session.last_proxy.port == http_proxy.port
    # The dead proxy is now cooling down, so later requests skip it entirely
    assert session.provider.available_proxies() == [http_proxy.proxy()]
    assert session.get(target.url, timeout=10).content == BODY


def test_post_is_retried_when_the_proxy_was_never_reached(http_proxy, target):
    session = session_for([dead_proxy(), http_proxy.proxy()])

    response = session.post(target.url, data={"a": "1"}, timeout=10)

    assert response.content == BODY
    assert target.hits == [("POST", "/")]


def test_raises_when_every_proxy_fails(target):
    session = session_for([dead_proxy(), dead_proxy(), dead_proxy()], max_retries=2)

    with pytest.raises(requests.exceptions.ConnectionError):
        session.get(target.url, timeout=10)

    assert target.hits == []
    assert session.provider.available_proxies() == []


def test_max_retries_zero_does_not_retry(http_proxy, target):
    session = session_for([dead_proxy(), http_proxy.proxy()], max_retries=0)

    with pytest.raises(requests.exceptions.ConnectionError):
        session.get(target.url, timeout=10)

    assert http_proxy.requests == []


def test_retry_statuses_moves_on_from_a_blocked_proxy(make_http_proxy, target):
    blocked = make_http_proxy(forced_status=403)
    working = make_http_proxy()
    session = session_for([blocked.proxy(), working.proxy()], retry_statuses={403})

    response = session.get(target.url, timeout=10)

    assert response.status_code == 200
    assert len(blocked.requests) == len(working.requests) == 1
    assert session.provider.available_proxies() == [working.proxy()]


def test_status_is_returned_as_is_without_retry_statuses(make_http_proxy, target):
    blocked = make_http_proxy(forced_status=403)
    working = make_http_proxy()
    session = session_for([blocked.proxy(), working.proxy()])

    assert session.get(target.url, timeout=10).status_code == 403
    assert working.requests == []
    assert len(session.provider.available_proxies()) == 2


def test_last_response_is_returned_when_every_proxy_is_blocked(make_http_proxy, target):
    proxies = [make_http_proxy(forced_status=429).proxy() for _ in range(2)]
    session = session_for(proxies, retry_statuses={429}, max_retries=1)

    assert session.get(target.url, timeout=10).status_code == 429


def test_wrong_credentials_can_be_treated_as_a_failed_proxy(make_http_proxy, target):
    bad = make_http_proxy()
    good = make_http_proxy()
    session = session_for(
        [bad.proxy(password="wrong"), good.proxy()], retry_statuses={407}
    )

    assert session.get(target.url, timeout=10).content == BODY
    assert bad.rejected == [target.url]


def test_explicit_proxies_argument_is_left_alone(make_http_proxy, target):
    rotating, explicit = make_http_proxy(), make_http_proxy()
    session = session_for([rotating.proxy()])

    session.get(target.url, proxies=explicit.proxy().format("requests"), timeout=10)

    assert rotating.requests == []
    assert len(explicit.requests) == 1


def test_streamed_body_is_not_retried(http_proxy, target):
    session = session_for([dead_proxy(), http_proxy.proxy()])

    with pytest.raises(requests.exceptions.ConnectionError):
        session.post(target.url, data=iter([b"chunk"]), timeout=10)

    assert http_proxy.requests == []


def test_algorithm_is_passed_to_the_provider(make_http_proxy, target):
    first, second = make_http_proxy(), make_http_proxy()
    session = session_for([first.proxy(), second.proxy()], algorithm=First())

    for _ in range(3):
        session.get(target.url, timeout=10)

    assert len(first.requests) == 3
    assert second.requests == []


def test_negative_max_retries_is_refused():
    with pytest.raises(ValueError):
        RotatingSession(ProxyList(["203.0.113.1:8080"]), max_retries=-1)


#
# Regression tests: never resend what may have reached the target
#


def test_post_is_not_resent_when_the_proxy_drops_after_relaying(
    make_http_proxy, target
):
    """requests raises ProxyError here too, so the error type alone must not allow a retry."""
    flaky = make_http_proxy(behaviour="drop_after_relay")
    good = make_http_proxy()
    session = session_for([flaky.proxy(), good.proxy()])

    with pytest.raises(requests.exceptions.ConnectionError):
        session.post(target.url, data={"charge": "100"}, timeout=10)

    assert target.hits == [("POST", "/")]  # exactly once
    assert good.requests == []
    assert session.provider.available_proxies() == [good.proxy()]


def test_get_is_resent_when_the_proxy_drops_after_relaying(make_http_proxy, target):
    flaky = make_http_proxy(behaviour="drop_after_relay")
    good = make_http_proxy()
    session = session_for([flaky.proxy(), good.proxy()])

    assert session.get(target.url, timeout=10).content == BODY
    assert len(good.requests) == 1


def test_hanging_proxy_is_reported_and_get_is_retried(make_http_proxy, target):
    hanging = make_http_proxy(behaviour="hang")
    good = make_http_proxy()
    session = session_for([hanging.proxy(), good.proxy()])

    assert session.get(target.url, timeout=0.5).content == BODY
    assert session.provider.available_proxies() == [good.proxy()]


def test_hanging_proxy_does_not_resend_a_post(make_http_proxy, target):
    hanging = make_http_proxy(behaviour="hang")
    good = make_http_proxy()
    session = session_for([hanging.proxy(), good.proxy()])

    with pytest.raises(requests.exceptions.Timeout):
        session.post(target.url, data={"a": "1"}, timeout=0.5)

    assert good.requests == []
    assert session.provider.available_proxies() == [good.proxy()]


def test_file_upload_is_not_retried(http_proxy, target, tmp_path):
    """A file is read to the end on the first attempt; a retry would upload nothing."""
    upload = tmp_path / "payload.txt"
    upload.write_text("IMPORTANT-PAYLOAD")
    session = session_for([dead_proxy(), http_proxy.proxy()])

    with open(upload, "rb") as handle:
        with pytest.raises(requests.exceptions.ConnectionError):
            session.post(target.url, files={"f": handle}, timeout=10)

    assert target.hits == []
    assert http_proxy.requests == []


def test_json_body_is_retried(http_proxy, target):
    session = session_for([dead_proxy(), http_proxy.proxy()])

    assert session.post(target.url, json={"a": 1}, timeout=10).content == BODY
    assert target.hits == [("POST", "/")]


def test_wrong_credentials_are_a_failed_proxy_by_default(make_http_proxy, target):
    """407 can only come from the proxy, so it needs no opt-in."""
    bad, good = make_http_proxy(), make_http_proxy()
    session = session_for([bad.proxy(password="wrong"), good.proxy()])

    assert session.get(target.url, timeout=10).content == BODY
    assert session.provider.available_proxies() == [good.proxy()]


def test_prepared_request_sent_with_send_is_rotated(http_proxy, target):
    """session.send() must not skip the proxy and go out directly."""
    session = session_for([dead_proxy(), http_proxy.proxy()])
    prepared = session.prepare_request(requests.Request("GET", target.url))

    response = session.send(prepared, timeout=10)

    assert response.content == BODY
    assert http_proxy.requests == [("GET", target.url)]


def test_send_with_explicit_proxies_is_left_alone(make_http_proxy, target):
    rotating, explicit = make_http_proxy(), make_http_proxy()
    session = session_for([rotating.proxy()])
    prepared = session.prepare_request(requests.Request("GET", target.url))

    session.send(prepared, proxies=explicit.proxy().format("requests"), timeout=10)

    assert rotating.requests == []
    assert len(explicit.requests) == 1


def test_each_request_goes_through_exactly_one_proxy_call(http_proxy, target):
    """The nested send() that requests makes must not rotate a second time."""
    session = session_for([http_proxy.proxy()])
    calls = []
    original = session.provider.get_proxy
    session.provider.get_proxy = lambda *a, **k: calls.append(1) or original(*a, **k)

    session.get(target.url, timeout=10)

    assert len(calls) == 1


def test_positional_arguments_are_accepted_like_requests(http_proxy, target):
    session = session_for([http_proxy.proxy()])

    response = session.request("GET", target.url, {"q": "1"}, None, None)

    assert response.content == BODY
    assert http_proxy.requests == [("GET", target.url + "?q=1")]


def test_tls_error_does_not_blame_the_proxy(http_proxy, monkeypatch):
    session = session_for([http_proxy.proxy()])

    def fail(self, request, **kwargs):
        raise requests.exceptions.SSLError("certificate verify failed")

    monkeypatch.setattr(requests.Session, "send", fail)
    with pytest.raises(requests.exceptions.SSLError):
        session.get("https://example.invalid/", timeout=10)

    assert len(session.provider.available_proxies()) == 1


def test_environment_proxies_do_not_replace_rotation(http_proxy, target, monkeypatch):
    """With trust_env on, HTTP_PROXY in the environment must not win over the provider."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    session = RotatingSession(ProxyList([http_proxy.proxy()]))

    assert session.get(target.url, timeout=10).content == BODY
    assert http_proxy.requests == [("GET", target.url)]


def test_post_is_retried_when_the_tunnel_cannot_be_opened(make_http_proxy):
    """For an https target a refused CONNECT means nothing reached the target."""
    first, second = make_http_proxy(), make_http_proxy()  # neither supports CONNECT
    session = session_for([first.proxy(), second.proxy()], max_retries=1)

    with pytest.raises(
        requests.exceptions.ProxyError, match="Tunnel connection failed"
    ):
        session.post("https://example.invalid/", data={"a": "1"}, timeout=10)

    # Both proxies were tried, which only happens if the failure counts as never sent
    assert session.provider.available_proxies() == []


def test_never_sent_recognises_a_connect_timeout_but_not_a_bare_proxy_error():
    from proxyproviders.session import _never_sent

    assert _never_sent(requests.exceptions.ConnectTimeout("timed out"))
    assert not _never_sent(requests.exceptions.ProxyError("connection dropped"))
    assert not _never_sent(requests.exceptions.ReadTimeout("slow"))


def test_post_is_not_resent_when_made_while_handling_another_error(
    make_http_proxy, target
):
    """Python links an error raised inside ``except`` to the one being handled. That
    earlier error says nothing about this request, so it must not make it look unsent."""
    flaky = make_http_proxy(behaviour="drop_after_relay")
    good = make_http_proxy()

    try:
        session_for([dead_proxy()], max_retries=0).get(target.url, timeout=10)
    except requests.exceptions.ConnectionError:
        session = session_for([flaky.proxy(), good.proxy()])
        with pytest.raises(requests.exceptions.ConnectionError):
            session.post(target.url, data={"charge": "100"}, timeout=10)

    assert target.hits == [("POST", "/")]  # exactly once
    assert good.requests == []
