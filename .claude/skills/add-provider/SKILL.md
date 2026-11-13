---
name: add-provider
description: Walk a contributor through adding a new proxy vendor (provider) to proxyproviders, from the first email to the maintainer through code, tests, docs, the affiliate link and the pull request. Use this whenever someone wants to add, contribute, integrate or support a proxy vendor or proxy service in this repo (e.g. "add Oxylabs", "support Smartproxy", "write a provider for my company's proxies", "how do I contribute a provider"), or is editing a file under proxyproviders/providers/, even if they never say the word "provider".
---

# Adding a proxy provider

A provider is one class that fetches proxies from a vendor and returns them as `Proxy`
objects. Everything else (caching, refresh, selection algorithms, output formats,
failure reporting, the rotating session) comes from the `ProxyProvider` base class, so
a good provider is small.

Work through the steps in order and tell the contributor where they are. Steps 1, 6, 7
and 9 each need something from the maintainer (a reply, a repository secret, the
affiliate links, the merge) and cannot be finished by code alone, so say so plainly
instead of working around them.

## 1. Check it is needed, then email the maintainer

Before writing code:

- Look in `proxyproviders/providers/` and at open pull requests (`gh pr list`) for the
  vendor, so two people do not build the same thing.
- If the contributor only needs to use proxies from this vendor in their own project,
  `ProxyList([...])` already does that with no new code. A provider is worth adding when
  the vendor has an API that lists proxies or credentials, or a username scheme
  (sessions, targeting) worth wrapping.

Then have the contributor email David Teather at **contact.davidteather@gmail.com**,
early, with:

- the vendor's name and a link to its API documentation
- whether the vendor has an affiliate or referral program, and a link to it
- whether they can provide a test account or API key for the integration tests
- whether they work for the vendor (welcome, and worth saying up front)

Why this comes first: two parts of a provider depend on the maintainer. The vendor links
in the docs go through the maintainer's redirect (step 7), and the integration tests
only run with a secret the maintainer adds to the repository (step 6). Sorting both out
while the code is being written avoids a finished pull request waiting on them. Offer to
draft this email. Credentials go in that email thread, never in an issue, a pull request
or a commit.

## 2. Set up

```bash
uv sync
uv tool install pre-commit && pre-commit install
uv run pytest tests/ --ignore=tests/integration -q   # should pass before you change anything
```

Read `proxyproviders/providers/webshare.py` (a vendor with a list API) and
`proxyproviders/providers/brightdata.py` (a gateway vendor where the username selects
the exit). Pick whichever is closer to the new vendor and follow its shape.

## 3. Write the provider

Create `proxyproviders/providers/<vendor>.py`:

```python
from typing import Any, Dict, List, Optional

import requests

from ..exceptions import (
    ProxyConversionException,
    ProxyFetchException,
    ProxyInvalidResponseException,
)
from ..models.proxy import Proxy
from ..proxy_provider import ProxyConfig, ProxyProvider


class YourVendor(ProxyProvider):
    """One paragraph on the vendor, then how to get an API key.

    :param api_key: Your YourVendor API key
    :param config: Configuration for the proxy provider. View the ProxyConfig class docs for more information.

    Example:

    .. code-block:: python

        from proxyproviders import YourVendor

        provider = YourVendor(api_key="your-api-key")
        proxies = provider.list_proxies()
    """

    _BASE_URL = "https://api.yourvendor.example"

    def __init__(self, api_key: str, config: Optional[ProxyConfig] = None):
        super().__init__(config)
        self.api_key = api_key

    def _fetch_proxies(self) -> List[Proxy]:
        try:
            response = requests.get(
                f"{self._BASE_URL}/proxies",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.config.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ProxyFetchException(f"Failed to fetch proxies: {str(e)}") from e

        try:
            results = response.json()["results"]
        except (ValueError, KeyError, TypeError) as e:
            # Not JSON, or JSON without the list we expect
            raise ProxyInvalidResponseException(response.text) from e

        return [self._convert_to_proxy(item) for item in results]

    def _convert_to_proxy(self, data: Dict[str, Any]) -> Proxy:
        try:
            return Proxy(
                id=str(data["id"]),
                username=data["username"],
                password=data["password"],
                proxy_address=data["host"],
                port=int(data["port"]),
                country_code=data.get("country_code"),
                protocols=["http", "https"],
            )
        except (KeyError, ValueError) as e:
            raise ProxyConversionException(
                f"Failed to convert proxy data: {str(e)}"
            ) from e
```

What to get right, and why:

- **Pass `timeout=self.config.timeout` to every HTTP call.** Without it a stalled
  connection hangs the user's program forever.
- **Raise the package's exceptions, not raw ones.** Users catch `ProxyProviderException`
  to handle any vendor the same way. Wrap `requests` errors in `ProxyFetchException`,
  unexpected response shapes in `ProxyInvalidResponseException`, and bad fields in
  `ProxyConversionException`.
- **Set `protocols` honestly, as a new list per proxy.** `["http", "https"]` for an HTTP
  proxy. For a SOCKS endpoint use `["socks5"]` on its own, which makes every output
  format use `socks5://`. Sharing one list object between proxies lets a change to one
  leak into all of them.
- **Take an API key when the vendor has an API.** Existing providers take `api_key` and
  look up what they need, which fails early on a bad key. Fall back to username and
  password only when there is no API.
- **Gateway vendors (username encodes session or location):** build the usernames in the
  provider, but create session ids once, not on every refresh. `list_proxies()`
  refreshes every `refresh_interval` seconds (600 by default), and a "sticky" session
  that changes each time is not sticky. Validate anything that gets concatenated into
  the username, so a stray value cannot inject extra parameters.
- **Never log or print credentials.** `Proxy` already hides its password from `repr()`;
  keep API keys out of exception messages too.
- **Type everything.** `uv run mypy` runs in strict mode in CI.

Do not add retries, ban detection or health checks to a provider. Those live in
`ProxyProvider.report_failure`, `RotatingSession` and the httpx transports, and work for
every provider already.

## 4. Export it

In `proxyproviders/__init__.py`, import the class and add its name to `__all__`.

## 5. Unit tests

Create `tests/providers/test_<vendor>.py`, modelled on `tests/providers/test_webshare.py`.
Mock the vendor's API with the `responses` library; unit tests must not touch the network.

Cover at least:

- a successful fetch converts every field correctly
- pagination, if the API paginates
- an HTTP error status raises `ProxyFetchException`
- a timeout or connection error raises `ProxyFetchException`
- a response missing the expected key raises `ProxyInvalidResponseException`
- an entry missing a required field raises `ProxyConversionException`
- `timeout=` is passed to the HTTP call
- `get_proxy()` returns a proxy and `format(ProxyFormat.REQUESTS)` looks right
- every constructor argument that is validated rejects bad input

```bash
uv run pytest tests/providers/test_<vendor>.py -q
uv run coverage run -m pytest tests/ --ignore=tests/integration && uv run coverage report --fail-under=95
```

CI fails under 95% coverage; aim for 100% of the new file.

## 6. Integration test (runs after merge)

Integration tests call the vendor's real API. They do **not** run on pull requests:
pull requests from forks have no access to repository secrets, and `ci.yml` skips
`tests/integration/`. They run in `.github/workflows/ci-main.yml` after the pull request
is merged to `main`, using a secret the maintainer adds. That is why the maintainer
needs a test key (step 1), and why the contributor must run the test locally first.

Create `tests/integration/test_<vendor>_integration.py`:

```python
import os

import pytest

from proxyproviders import YourVendor

skip_integration = pytest.mark.skipif(
    not (os.getenv("RUN_INTEGRATION_TESTS") and os.getenv("YOURVENDOR_API_KEY")),
    reason="Integration tests require RUN_INTEGRATION_TESTS and YOURVENDOR_API_KEY",
)


@skip_integration
def test_yourvendor_integration():
    provider = YourVendor(api_key=os.environ["YOURVENDOR_API_KEY"])

    proxies = provider.list_proxies(force_refresh=True)

    assert proxies
    for proxy in proxies:
        assert proxy.proxy_address
        assert isinstance(proxy.port, int)
```

Then:

- Add the secret to the test step's `env:` block in `.github/workflows/ci-main.yml`,
  next to `WEBSHARE_API_KEY`:
  `YOURVENDOR_API_KEY: ${{ secrets.YOURVENDOR_API_KEY }}`. The test skips itself until
  the maintainer has added the secret, so this is safe to merge first.
- Run it locally with a real key and keep the output for the pull request:
  `RUN_INTEGRATION_TESTS=1 YOURVENDOR_API_KEY=... uv run pytest tests/integration/test_<vendor>_integration.py -v`
- Prefer checks that call the vendor's API over ones that send traffic through a proxy.
  Proxy traffic costs money on every push to `main`. If a request through the proxy is
  the only meaningful check, make one small request.

If the contributor has no key and cannot get one, say so in the pull request instead of
skipping this step silently. An untested provider can still be reviewed, but the
maintainer needs to know.

## 7. Documentation and the affiliate link

Add the provider to each place users look:

- `.sphinx/providers/<vendor>.rst`, copying `.sphinx/providers/webshare.rst`, and an
  `.. include::` for it plus a bullet in `.sphinx/proxyproviders.rst`
- the "Supported Proxy Providers" table and the "Getting credentials" list in `README.md`
- the provider list in `.sphinx/llms.txt`
- the class docstring (how to get credentials, every parameter, a working example)

**Vendor links.** The existing providers link to the vendor through the maintainer's
redirect, labelled as an affiliate link:

```
https://go.dteather.com/<vendor>?src=proxyproviders&placement=readme      (README.md)
https://go.dteather.com/<vendor>?src=proxyproviders&placement=docs        (.sphinx/proxyproviders.rst)
https://go.dteather.com/<vendor>?src=proxyproviders&placement=docstring   (the class docstring)
```

Those redirects are created by the maintainer, so one for a new vendor does not exist
yet. In the pull request, link to the vendor's plain homepage in those three places and
say in the description that the links are placeholders. Do not invent a
`go.dteather.com` URL, and do not use the contributor's own referral link: the
maintainer replaces the three links before merging, once the affiliate arrangement from
step 1 is in place. This is how the project is funded, and it is disclosed next to every
link.

## 8. Check everything

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run coverage run -m pytest tests/ --ignore=tests/integration && uv run coverage report --fail-under=95
pre-commit run --all-files
```

CI runs ruff, mypy and the unit tests with the coverage floor on the pull request.
The pre-commit hooks run the same checks locally before each commit.

## 9. Open the pull request

Ask the contributor before pushing a branch or opening the pull request: both are
visible to other people, so they are the contributor's call, not something to do
unprompted. Show them the title and description first.

Title: `feat: add <Vendor> provider`. In the description include:

- what the vendor is and a link to its API docs
- how a user gets an API key
- what the provider supports and what it leaves out
- the coverage figure, and the output of the local integration test run
- a note that the vendor links are placeholders for the maintainer's affiliate links
- whether the contributor works for the vendor
- confirmation that the maintainer was emailed (step 1), or a note that they still need to be

After it is opened, the maintainer reviews the code, sets up the affiliate link and the
repository secret, and merges. The integration test then runs on `main`. If it fails
there, the contributor may be asked to follow up, so it is worth watching the first run.

## Finishing up

Before telling the contributor they are done, confirm each of these, and name any that
are not:

- [ ] maintainer emailed about the affiliate link and a test key
- [ ] provider class, exported from `proxyproviders/__init__.py`
- [ ] unit tests with the API mocked, coverage at or above 95%
- [ ] integration test, skipped without credentials, run locally with real ones
- [ ] secret name added to `ci-main.yml`
- [ ] docs page, README table, `llms.txt` and docstring updated
- [ ] vendor links are plain placeholders, flagged in the pull request
- [ ] ruff, mypy and the tests pass
