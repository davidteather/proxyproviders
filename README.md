# ProxyProviders

One interface for proxy vendors, many Python clients.

Get proxies from Webshare, Bright Data or your own list, and use them with requests, httpx, aiohttp, Playwright, Scrapy, Crawlee or curl without writing vendor-specific code. Swap providers by changing one line.

 [![codecov](https://codecov.io/gh/davidteather/proxyproviders/graph/badge.svg?token=MZF0KP7YMA)](https://codecov.io/gh/davidteather/proxyproviders) [![Sponsor Me](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub)](https://go.dteather.com/github-sponsors?src=proxyproviders&placement=badge) [![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidteather/proxyproviders)](https://github.com/davidteather/proxyproviders/releases) [![GitHub](https://img.shields.io/github/license/davidteather/proxyproviders)](https://github.com/davidteather/proxyproviders/blob/main/LICENSE) [![Downloads](https://pepy.tech/badge/proxyproviders)](https://pypi.org/project/proxyproviders/) ![](https://visitor-badge.laobi.icu/badge?page_id=davidteather.proxyproviders) [![Support Server](https://img.shields.io/discord/783108952111579166.svg?color=7289da&logo=discord&style=flat-square)](https://go.dteather.com/discord?src=proxyproviders&placement=badge) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white&style=flat-square)](https://www.linkedin.com/in/davidteather/)

```py
import requests
from proxyproviders import Webshare, ProxyFormat

provider = Webshare(api_key="your-api-key")  # or BrightData(...), or ProxyList([...])
proxy = provider.get_proxy()

response = requests.get(
    "https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS)
)
```

## Table of Contents

- [Installation](#installation)
- [What It Does](#what-it-does)
- [Works With](#works-with)
- [Supported Proxy Providers](#supported-proxy-providers)
- [Quick Start Guide](#quick-start-guide)
- [Using Proxies With Your HTTP Client](#using-proxies-with-your-http-client)
  - [requests](#python-requests-with-rotating-proxies)
  - [httpx](#httpx-proxy)
  - [aiohttp](#aiohttp-proxy)
  - [Playwright](#playwright-proxy-in-python)
  - [Scrapy](#scrapy-proxy)
  - [Crawlee](#crawlee-for-python-proxy)
  - [curl and subprocesses](#curl-and-subprocesses)
- [Use Your Own Proxy List](#use-your-own-proxy-list)
- [Automatic Rotation and Retries](#automatic-rotation-and-retries)
- [Reporting Failed Proxies](#reporting-failed-proxies)
- [Choosing Which Proxy You Get](#choosing-which-proxy-you-get)
- [Configuration](#configuration)
- [SOCKS Proxies](#socks-proxies)
- [Making Your Own Proxy Provider](#making-your-own-proxy-provider)
- [How to Support The Project](#how-to-support-the-project)

## Installation

```sh
python -m pip install proxyproviders
```

Python 3.10 or newer. The full documentation is [here](https://davidteather.github.io/proxyproviders), and there are runnable [examples in the repository](https://github.com/davidteather/proxyproviders/tree/main/examples).

Using an AI coding assistant? Point it at [llms.txt](https://davidteather.github.io/proxyproviders/llms.txt), a short summary of the API written for assistants.

**📺 Video Tutorial:** [Watch the quick start guide on YouTube](https://youtu.be/h-JouO_orYo) for a walkthrough of getting started with ProxyProviders.

## What It Does

Every proxy vendor has its own API, and every HTTP client wants its proxy in a different shape. ProxyProviders sits between the two:

```text
Webshare | Bright Data | your own list
                 ↓
   ProxyProvider  →  Proxy
                 ↓
requests | httpx | aiohttp | Playwright | Scrapy | Crawlee | curl
```

- **Provider API handled for you.** Proxies are fetched from the vendor, cached, and refreshed on an interval.
- **One `Proxy` model.** Host, port, credentials, country and protocols look the same whichever vendor they came from.
- **One line to hand it to your client.** `proxy.format(...)` produces what each client expects, with credentials percent-encoded correctly.
- **Vendor-neutral code.** Anything written against `ProxyProvider` works with every provider, so switching vendor does not touch the rest of your application.

Rotation and retries are available if you want them ([`RotatingSession`](#automatic-rotation-and-retries)), and stay out of the way if your framework already does that.

## Works With

| Client | How to pass the proxy | Format |
|---|---|---|
| [requests](#python-requests-with-rotating-proxies) | `requests.get(url, proxies=...)` | `ProxyFormat.REQUESTS` |
| [httpx](#httpx-proxy) | `httpx.Client(proxy=...)` | `ProxyFormat.HTTPX` |
| [aiohttp](#aiohttp-proxy) | `session.get(url, proxy=...)` | `ProxyFormat.AIOHTTP` |
| [Playwright](#playwright-proxy-in-python) | `browser.new_context(proxy=...)` | `ProxyFormat.PLAYWRIGHT` |
| [Scrapy](#scrapy-proxy) | `Request(meta={"proxy": ...})` | `ProxyFormat.SCRAPY` |
| [Crawlee](#crawlee-for-python-proxy) | `ProxyConfiguration(proxy_urls=[...])` | `proxy.to_url()` |
| urllib | `urllib.request.ProxyHandler(...)` | `ProxyFormat.URLLIB` |
| [curl](#curl-and-subprocesses) | `curl -x ...` | `ProxyFormat.CURL` |
| [Any subprocess](#curl-and-subprocesses) | `HTTP_PROXY` / `HTTPS_PROXY` variables | `ProxyFormat.ENV` |
| Other tools | `host:port:username:password` | `ProxyFormat.HOST_PORT_USER_PASS` |
| Anything else | `scheme://username:password@host:port` | `ProxyFormat.URL` |

requests, httpx, aiohttp, urllib and curl are tested in CI by sending a real request through a local proxy with each client's current release.

## Supported Proxy Providers

| Provider | Class | Notes |
|---|---|---|
| Webshare | `Webshare(api_key=...)` | 10 free datacenter proxies to try it out |
| Bright Data | `BrightData(api_key=..., zone=...)` | Super proxy or one proxy per IP in the zone |
| Any other vendor | `ProxyList([...])` | [Your own list](#use-your-own-proxy-list) of proxy URLs or `host:port:user:pass` lines |

Getting credentials:

- **Webshare:** create an account [here](https://go.dteather.com/webshare?src=proxyproviders&placement=readme) (affiliate link), then generate a token in the [API tab](https://dashboard.webshare.io/userapi/keys).
- **Bright Data:** create an account [here](https://go.dteather.com/brightdata?src=proxyproviders&placement=readme) (affiliate link), then create an API token in the [account settings](https://brightdata.com/cp/setting/users).

Keep API tokens out of your code and repository; the examples below read them from environment variables. Each provider's options are in the [provider documentation](https://davidteather.github.io/proxyproviders/#proxyproviders-supported-providers). Don't see your vendor? [Add a provider](#making-your-own-proxy-provider) or open an issue.

## Quick Start Guide

List the proxies from a provider:

```py
import os
from proxyproviders import Webshare

provider = Webshare(api_key=os.environ["WEBSHARE_API_KEY"])

proxies = provider.list_proxies()
print(proxies)  # passwords are left out of the printed output
```

Or take one at a time. `get_proxy()` cycles through the list in order by default:

```py
proxy = provider.get_proxy()
print(proxy.proxy_address, proxy.port, proxy.country_code)
```

Providers take their own options. `Webshare` passes `search_params` to the [Webshare API](https://apidocs.webshare.io/proxy-list/list#parameters), so this returns only proxies based in the US:

```py
provider = Webshare(
    api_key=os.environ["WEBSHARE_API_KEY"], search_params={"country_code_in": "US"}
)
```

Because every provider has the same interface, code written against `ProxyProvider` does not care which vendor is behind it:

```py
import os
import requests
from proxyproviders import BrightData, ProxyFormat, ProxyProvider, Webshare


def fetch_ip(provider: ProxyProvider) -> str:
    proxy = provider.get_proxy()
    response = requests.get(
        "https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS)
    )
    return response.json()["origin"]


fetch_ip(Webshare(api_key=os.environ["WEBSHARE_API_KEY"]))
fetch_ip(BrightData(api_key=os.environ["BRIGHTDATA_API_KEY"], zone="my_zone"))
```

That is how other libraries, such as my [TikTokAPI](https://go.dteather.com/tiktokapi?src=proxyproviders&placement=readme) package, accept any proxy vendor without knowing about it.

## Using Proxies With Your HTTP Client

Every example below starts with a `provider`, which can be any provider from the table above.

### Python requests With Rotating Proxies

```py
import requests
from proxyproviders import ProxyFormat

proxy = provider.get_proxy()
response = requests.get(
    "https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS)
)
```

Each `get_proxy()` call returns the next proxy, so calling it per request rotates through your proxies. To have rotation and retries done for you, use [`RotatingSession`](#automatic-rotation-and-retries).

### httpx Proxy

httpx (0.26 or newer) takes one proxy URL in its `proxy=` argument, for both the sync and async clients:

```py
import httpx
from proxyproviders import ProxyFormat

with httpx.Client(proxy=provider.get_proxy().format(ProxyFormat.HTTPX)) as client:
    response = client.get("https://httpbin.org/ip")

async with httpx.AsyncClient(
    proxy=provider.get_proxy().format(ProxyFormat.HTTPX)
) as client:
    response = await client.get("https://httpbin.org/ip")
```

### aiohttp Proxy

```py
import aiohttp
from proxyproviders import ProxyFormat

async with aiohttp.ClientSession() as session:
    async with session.get(
        "https://httpbin.org/ip", proxy=provider.get_proxy().format(ProxyFormat.AIOHTTP)
    ) as response:
        print(await response.json())
```

### Playwright Proxy in Python

```py
from playwright.sync_api import sync_playwright
from proxyproviders import ProxyFormat

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        proxy=provider.get_proxy().format(ProxyFormat.PLAYWRIGHT)
    )
    page = context.new_page()
    page.goto("https://httpbin.org/ip")
```

Give each browser context its own `get_proxy()` call to spread contexts across proxies. The same dictionary works for `p.chromium.launch(proxy=...)`.

### Scrapy Proxy

Scrapy's built-in `HttpProxyMiddleware` reads the proxy from `request.meta` and takes the credentials out of the URL:

```py
import scrapy
from proxyproviders import ProxyFormat


class IpSpider(scrapy.Spider):
    name = "ip"

    def start_requests(self):
        yield scrapy.Request(
            "https://httpbin.org/ip",
            meta={"proxy": provider.get_proxy().format(ProxyFormat.SCRAPY)},
        )
```

### Crawlee for Python Proxy

Crawlee rotates proxies and manages sessions itself, so hand it the whole list:

```py
from crawlee.proxy_configuration import ProxyConfiguration

proxy_configuration = ProxyConfiguration(
    proxy_urls=[proxy.to_url() for proxy in provider.list_proxies()]
)
```

### curl and Subprocesses

```py
import os
import subprocess
from proxyproviders import ProxyFormat

proxy = provider.get_proxy()

# As curl arguments: ["-x", "http://user:pass@host:port"]
subprocess.run(["curl", *proxy.format(ProxyFormat.CURL), "https://httpbin.org/ip"])

# Or as HTTP_PROXY / HTTPS_PROXY for any program that reads them
subprocess.run(
    ["curl", "https://httpbin.org/ip"],
    env={**os.environ, **proxy.format(ProxyFormat.ENV)},
)
```

## Use Your Own Proxy List

If your vendor has no provider here, or you simply have a list of proxies, `ProxyList` gives them the same interface as everything else:

```py
from proxyproviders import ProxyList

provider = ProxyList(
    [
        "http://user:pass@203.0.113.7:8080",
        "203.0.113.8:8080:user:pass",
        "socks5://user:pass@203.0.113.9:1080",
    ]
)

# Or one proxy per line from a file (blank lines and # comments are skipped)
provider = ProxyList.from_file("proxies.txt")
```

A single proxy can be parsed with `Proxy.from_string(...)`, which accepts a URL, `user:pass@host:port`, `host:port` or `host:port:user:pass`.

## Automatic Rotation and Retries

`RotatingSession` is a `requests.Session` that picks a proxy for every request. If a request cannot get through its proxy, that proxy is set aside for a while and the request is sent again through the next one:

```py
from proxyproviders import RotatingSession

session = RotatingSession(provider, max_retries=3)

response = session.get("https://httpbin.org/ip", timeout=10)
print(response.json(), session.last_proxy)
```

It is opt-in: nothing changes for code that calls `get_proxy()` itself. What it treats as a failed proxy, and when it sends the request again:

- **Could not connect to the proxy, or open a tunnel through it:** retried for any HTTP method, because the request never reached the target.
- **Any other connection error or timeout**, such as a proxy that drops the connection or stops responding: retried for `GET`, `HEAD` and `OPTIONS` only. A `POST` may already have been acted on, so the error is raised instead of sending it twice.
- **A `407 Proxy Authentication Required` response**, or any status you list in `retry_statuses`: retried for any method.

Ordinary error statuses such as 404 or 500 are returned as usual. File uploads and streamed bodies are sent once and never retried. Deciding that a response means your proxy is blocked is up to you, for example:

```py
session = RotatingSession(provider, max_retries=3, retry_statuses={403, 429})
```

For httpx 0.26 or newer, sync or async, the same behaviour comes as a transport. Install it with `pip install "proxyproviders[httpx]"`:

```py
import httpx
from proxyproviders.httpx_transport import AsyncRotatingTransport, RotatingTransport

with httpx.Client(transport=RotatingTransport(provider, max_retries=3)) as client:
    response = client.get("https://httpbin.org/ip")

async with httpx.AsyncClient(transport=AsyncRotatingTransport(provider)) as client:
    response = await client.get("https://httpbin.org/ip")
```

## Reporting Failed Proxies

When you make requests yourself, tell the provider about a proxy that failed and `get_proxy()` will avoid it for `failure_cooldown` seconds (60 by default):

```py
import requests
from proxyproviders import ProxyFormat

proxy = provider.get_proxy()
try:
    response = requests.get(url, proxies=proxy.format(ProxyFormat.REQUESTS), timeout=10)
except requests.exceptions.ProxyError:
    provider.report_failure(proxy)
```

`provider.report_success(proxy)` puts it back early, and `provider.available_proxies()` lists the ones not currently set aside. If every proxy has failed, `get_proxy()` still returns one instead of raising. This works the same with every HTTP client, sync or async.

## Choosing Which Proxy You Get

`get_proxy()` takes a selection algorithm. The default is round robin.

```py
from proxyproviders.algorithms import First, Random, RoundRobin

proxy = provider.get_proxy()  # RoundRobin: next proxy in order
proxy = provider.get_proxy(Random())  # a random proxy
proxy = provider.get_proxy(First())  # always the first proxy

# A RoundRobin you create keeps its own position, separate from the provider's default
round_robin = RoundRobin()
proxy1 = provider.get_proxy(round_robin)
proxy2 = provider.get_proxy(round_robin)  # next in sequence
```

Write your own by subclassing `Algorithm`:

```py
from typing import List
from proxyproviders import Proxy
from proxyproviders.algorithms import Algorithm


class USProxyAlgorithm(Algorithm):
    """Prefers US proxies, falls back to the first available."""

    def select(self, proxies: List[Proxy]) -> Proxy:
        for proxy in proxies:
            if proxy.country_code == "US":
                return proxy
        return proxies[0]


proxy = provider.get_proxy(USProxyAlgorithm())
```

## Configuration

Options shared by every provider live in `ProxyConfig` ([full reference](https://davidteather.github.io/proxyproviders/#proxyproviders.proxy_provider.ProxyConfig)):

| Option | Default | Meaning |
|---|---|---|
| `refresh_interval` | 600 | Seconds before the proxy list is fetched again. 0 fetches once and never refreshes. |
| `timeout` | 30 | Seconds to wait on each call to the provider's API |
| `refresh_retry_delay` | 30 | If a refresh fails, the previous list keeps being served and the API is tried again after this many seconds |
| `failure_cooldown` | 60 | Seconds `get_proxy()` avoids a proxy after `report_failure()` |

```py
import os
import time
from proxyproviders import ProxyConfig, Webshare

config = ProxyConfig(refresh_interval=3)
ws = Webshare(api_key=os.environ["WEBSHARE_API_KEY"], config=config)

ws.list_proxies()  # calls the API
ws.list_proxies()  # cached

time.sleep(5)
ws.list_proxies()  # calls the API again, since more than 3s have passed
```

`list_proxies()` and `get_proxy()` are safe to call from several threads.

## SOCKS Proxies

A proxy whose `protocols` only lists a SOCKS scheme, e.g. `["socks5"]`, is formatted with that scheme for every client:

```py
proxy.format(ProxyFormat.REQUESTS)
# {'http': 'socks5://user:pass@host:1080', 'https': 'socks5://user:pass@host:1080'}
```

Your HTTP client needs SOCKS support for this to work. For requests, install it with:

```sh
python -m pip install "proxyproviders[socks]"
```

httpx needs `httpx[socks]`. aiohttp and Scrapy have no built-in SOCKS support.

## Making Your Own Proxy Provider

Subclass `ProxyProvider` and return a list of `Proxy` objects from `_fetch_proxies`. Caching, refreshing, selection, formatting and failure reporting then work without any more code:

```py
from typing import List, Optional
from proxyproviders import Proxy, ProxyConfig, ProxyProvider


class MyProxyProvider(ProxyProvider):
    def __init__(self, config: Optional[ProxyConfig] = None):
        super().__init__(config=config)

    def _fetch_proxies(self) -> List[Proxy]:
        # Call your vendor's API here and convert each entry
        return [
            Proxy(
                id="1",
                username="username",
                password="password",
                proxy_address="192.168.1.1",
                port=80,
            )
        ]


provider = MyProxyProvider()
proxy = provider.get_proxy()
```

If you write one for a vendor other people use, please contribute it back. [CONTRIBUTING.md](https://github.com/davidteather/proxyproviders/blob/main/CONTRIBUTING.md) has the steps, and the repository includes an `add-provider` skill that walks a coding agent such as Claude Code through the whole process.

## How to Support The Project

- Star the repo 😎
- Consider [sponsoring](https://go.dteather.com/github-sponsors?src=proxyproviders&placement=readme) me on GitHub
- Send me an email or a [LinkedIn](https://www.linkedin.com/in/davidteather/) message about what you're doing with it :D
- Submit PRs for issues or any new providers/features :)

**Note:** If you want to learn how to web scrape websites check my [free and open-source course for learning everything web scraping](https://go.dteather.com/everything-web-scraping?src=proxyproviders&placement=readme)
