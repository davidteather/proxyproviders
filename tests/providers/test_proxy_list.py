import pytest

from proxyproviders import Proxy, ProxyFormat, ProxyList
from proxyproviders.algorithms import First


def test_accepts_text_and_proxy_objects():
    existing = Proxy(
        id="obj", username="u", password="p", proxy_address="198.51.100.1", port=8000
    )
    provider = ProxyList(
        [
            "http://user:pass@203.0.113.7:8080",
            "203.0.113.8:8080:user:pass",
            "socks5://user:pass@203.0.113.9:1080",
            existing,
        ]
    )

    proxies = provider.list_proxies()
    assert [p.proxy_address for p in proxies] == [
        "203.0.113.7",
        "203.0.113.8",
        "203.0.113.9",
        "198.51.100.1",
    ]
    assert proxies[2].scheme == "socks5"
    assert proxies[3] is existing


def test_behaves_like_any_other_provider():
    provider = ProxyList(["203.0.113.7:8080:user:pass", "203.0.113.8:8080:user:pass"])

    assert [provider.get_proxy().proxy_address for _ in range(3)] == [
        "203.0.113.7",
        "203.0.113.8",
        "203.0.113.7",
    ]
    assert provider.get_proxy(First()).format(ProxyFormat.REQUESTS) == {
        "http": "http://user:pass@203.0.113.7:8080",
        "https": "http://user:pass@203.0.113.7:8080",
    }


def test_from_file_skips_blank_lines_and_comments(tmp_path):
    path = tmp_path / "proxies.txt"
    path.write_text(
        "# my proxies\n\n203.0.113.7:8080:user:pass\n  \n"
        "  http://user:pass@203.0.113.8:8080  \n# end\n"
    )

    provider = ProxyList.from_file(path)
    assert [p.proxy_address for p in provider.list_proxies()] == [
        "203.0.113.7",
        "203.0.113.8",
    ]
    assert ProxyList.from_file(str(path)).list_proxies() == provider.list_proxies()


def test_bad_entry_is_reported_up_front():
    with pytest.raises(ValueError, match="not-a-proxy"):
        ProxyList(["203.0.113.7:8080", "not-a-proxy"])


def test_empty_list_is_refused(tmp_path):
    with pytest.raises(ValueError, match="at least one proxy"):
        ProxyList([])

    path = tmp_path / "empty.txt"
    path.write_text("# nothing here\n")
    with pytest.raises(ValueError, match="at least one proxy"):
        ProxyList.from_file(path)


def test_changing_the_returned_list_does_not_change_the_provider():
    provider = ProxyList(["203.0.113.7:8080"])
    provider.list_proxies().clear()
    assert len(provider.list_proxies(force_refresh=True)) == 1


def test_from_file_ignores_a_byte_order_mark(tmp_path):
    """Files saved by Windows editors start with a BOM, which must not join the host."""
    path = tmp_path / "bom.txt"
    path.write_bytes("﻿# exported\n203.0.113.7:8080:user:pass\n".encode("utf-8"))

    provider = ProxyList.from_file(path)
    assert [p.proxy_address for p in provider.list_proxies()] == ["203.0.113.7"]


def test_password_with_at_sign_in_a_file(tmp_path):
    path = tmp_path / "proxies.txt"
    path.write_text("203.0.113.7:8080:user:p@ss\n")

    proxy = ProxyList.from_file(path).list_proxies()[0]
    assert (proxy.proxy_address, proxy.password) == ("203.0.113.7", "p@ss")
