# AGENTS.md

Guidance for AI coding agents working in this repository. Humans should start with
[README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

If you are helping someone **use** proxyproviders in their own project, not change it,
read [.sphinx/llms.txt](.sphinx/llms.txt) instead: it is a short, accurate summary of
the public API and the mistakes assistants most often make with it.

## What this project is

`proxyproviders` is a small Python library with one job: give every proxy vendor the
same interface, and turn each proxy into the shape an HTTP client expects.

```text
vendor API or your own list  →  ProxyProvider  →  Proxy  →  proxy.format(...)  →  requests, httpx, aiohttp, Playwright, ...
```

It is deliberately thin. Vendor-neutral sourcing and formatting are the core. Rotation
and retries exist only as opt-in helpers. Crawling, ban detection, captcha handling and
browser fingerprinting belong to the frameworks this library feeds, and should not be
added here.

## Commands

The project uses [uv](https://docs.astral.sh/uv/). Do not use pip or Poetry.

```bash
uv sync                                    # install the package and dev dependencies
uv run pytest tests/ --ignore=tests/integration -q    # unit tests (no network, no keys)
uv run mypy                                # strict type checking of the package
uv run ruff check . && uv run ruff format --check .   # lint and formatting
uv run ruff check --fix . && uv run ruff format .     # apply fixes
uv run coverage run -m pytest tests/ --ignore=tests/integration && uv run coverage report --fail-under=95
cd .sphinx && uv run --group docs make html           # build the docs
uv build                                   # build the wheel and sdist
```

CI runs ruff, mypy and the unit tests with a 95% coverage floor on Python 3.10 to 3.13.
Run all four before saying a change is finished.

## Layout

| Path | What lives there |
|---|---|
| `proxyproviders/proxy_provider.py` | `ProxyProvider` base class and `ProxyConfig`: caching, thread-safe refresh, `get_proxy`, failure reporting |
| `proxyproviders/models/proxy.py` | The `Proxy` dataclass, `to_url`, `from_string` |
| `proxyproviders/models/formats.py` | `ProxyFormat` and one small function per output format, plus the text parser |
| `proxyproviders/providers/` | One module per vendor (`webshare.py`, `brightdata.py`) and `proxy_list.py` for user-supplied lists |
| `proxyproviders/algorithms.py` | Selection algorithms: `RoundRobin`, `Random`, `First` |
| `proxyproviders/session.py` | `RotatingSession`, the opt-in `requests.Session` |
| `proxyproviders/httpx_transport.py` | Opt-in rotating transports for httpx, sync and async. The only module that imports httpx |
| `proxyproviders/exceptions.py` | The exception hierarchy under `ProxyProviderException` |
| `tests/` | Unit tests. `tests/local_servers.py` has a local target server and proxy for end-to-end tests |
| `tests/integration/` | Tests that call real vendor APIs. Skipped unless credentials are set |
| `.sphinx/` | Documentation source, including `llms.txt` |
| `examples/` | Runnable examples |

## Rules that are easy to break

- **Do not change what existing public calls return.** `list_proxies()`, `get_proxy()`,
  `Proxy.format()` and `Proxy.to_url()` are used by other packages, including TikTokApi.
  New behaviour is added as something a user opts into: a new method, a new format, a
  new class.
- **`requests` is the only runtime dependency.** Anything needing another library goes
  in its own module behind an optional extra, as `httpx_transport.py` does.
- **Unit tests never touch the network.** Mock vendor APIs with `responses`. For
  anything that must send real traffic, use the fixtures in `tests/conftest.py`
  (`target`, `http_proxy`, `make_http_proxy`), which run on localhost.
- **Prove a client format with the real client.** A format is only correct if the named
  library accepts it. `tests/test_client_compat.py` sends a request through a local
  proxy with each client; add to it when you add or change a format.
- **Never put credentials in code, tests, logs, exception messages or examples.**
  `Proxy.password` is hidden from `repr()` on purpose. Examples read keys from
  environment variables.
- **Every provider HTTP call passes `timeout=self.config.timeout`** and raises the
  package's own exceptions, not raw `requests` ones.
- **Keep it typed.** mypy runs in strict mode; do not add `# type: ignore` without a
  specific error code and a reason.
- **Docs are part of the change.** A new provider, format or public method needs the
  README, the relevant `.sphinx/` page and `.sphinx/llms.txt` updated in the same change.

## Common tasks

**Add a proxy vendor.** Follow the `add-provider` skill in
`.claude/skills/add-provider/SKILL.md`. It covers the whole process, including the two
steps that need the maintainer: the affiliate link and the integration-test secret.

**Add an output format.** In `proxyproviders/models/formats.py`, add a `ProxyFormat`
member with a docstring saying exactly which argument of which library it is passed to,
write a `_format_<name>(proxy, **kwargs)` function, and register it in `_FORMATTERS`.
Add a unit test in `tests/test_formats.py`, an end-to-end test in
`tests/test_client_compat.py` if the client can run in CI, and a row in the README's
"Works With" table.

**Add a selection algorithm.** Subclass `Algorithm` in `proxyproviders/algorithms.py`
and implement `select(proxies)`. It receives only proxies that are not cooling down
after `report_failure`, and must raise `ValueError` on an empty list.

## Releasing (maintainer only)

Do not bump the version, tag, publish or push to `main` unless the maintainer asks. The
version lives in `pyproject.toml` and `proxyproviders/version.py`; `bump2version` updates
both. Publishing a GitHub release triggers `.github/workflows/publish.yml`, which builds
with `uv build` and uploads to PyPI.

## Maintainer

David Teather, contact.davidteather@gmail.com. Contributors adding a provider should
email before or while opening the pull request; the `add-provider` skill explains why.
