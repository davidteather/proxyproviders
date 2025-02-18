# ProxyProviders
Unified python interface for proxy provider APIs, supports BrightData, WebShare, and more.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white&style=flat-square)](https://www.linkedin.com/in/davidteather/) [![Sponsor Me](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub)](https://github.com/sponsors/davidteather) [![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidteather/proxyproviders)](https://github.com/davidteather/proxyproviders/releases) [![GitHub](https://img.shields.io/github/license/davidteather/proxyproviders)](https://github.com/davidteather/proxyproviders/blob/main/LICENSE) [![Downloads](https://pepy.tech/badge/proxyproviders)](https://pypi.org/project/proxyproviders/) ![](https://visitor-badge.laobi.icu/badge?page_id=davidteather.proxyproviders) [![Support Server](https://img.shields.io/discord/783108952111579166.svg?color=7289da&logo=discord&style=flat-square)](https://discord.gg/yyPhbfma6f)

## Table of Contents

- [Documentation](#documentation)
- [Getting Started](#getting-started)
  - [How to Support The Project](#how-to-support-the-project)
  - [Installing](#installing)
- [Quick Start Guide](#quick-start-guide)
  - [Examples](https://github.com/davidteather/proxyproviders/tree/main/examples)

## Documentation

You can find the full documentation [here](https://davidteather.github.io/proxyproviders)

**Note:** If you want to learn how to web scrape websites check my [free and open-source course for learning everything web scraping](https://github.com/davidteather/everything-web-scraping)

### How to Support The Project

- Star the repo 😎
- Consider [sponsoring](https://github.com/sponsors/davidteather) me on GitHub
- Send me an email or a [LinkedIn](https://www.linkedin.com/in/davidteather/) message about what you're doing with it :D 
- Submit PRs for issues or any new providers/features :)

## Getting Started

To get started using this package follow the instructions below.

### Installation

This package is installable via pip.
```sh
python -m pip install proxyproviders
```

## Quick Start Guide

Here's a quick bit of code to get you started! There's also a few [examples in the folder](https://github.com/davidteather/proxyproviders/tree/main/examples). 

**Note:** If you want to learn how to web scrape websites check my [free and open-source course for learning everything web scraping](https://github.com/davidteather/everything-web-scraping)

### Choose a Proxy Provider

If you already haven't, choose which proxy provider to use. You can find a [list in the documentation](https://davidteather.github.io/proxyproviders/#proxyproviders-supported-providers). After choosing, look at the documentation around the specific provider you've choosen. Where needed, we've laid out steps to get api keys in the documentation. These steps will vary slightly by provider. For this example I'll be using the [Webshare Provider](https://davidteather.github.io/proxyproviders/#proxyproviders.providers.webshare.Webshare) because it's both easy to setup and they give you 10 free data center proxies to test out.

You can create an account on webshare [here](https://www.webshare.io/?referral_code=3x5812idzzzp) (affiliate link), then head into the [API tab](https://dashboard.webshare.io/userapi/keys) on the side and generate a new token. Keep this API token safe and don't post it publically.

### Basic Example

After you can list out your proxies with
```py
from proxyproviders import Webshare

proxy_provider = Webshare(api_key="your-api-key")

proxies = proxy_provider.list_proxies()

print(proxies)
```

Each provider has their own custom options, the `Webshare` class lets you specify url params according to their [api spec](https://apidocs.webshare.io/proxy-list/list#parameters), here's an example which will only return proxies that are based in the US.

```py
proxy_provider = Webshare(api_key="your-api-key", params={"country_code_in": "US"})
```

### Using ProxyConfig

For any shared logic across all types of proxy providers, we use the `ProxyConfig` data class to configure them. The full docs for [ProxyConfig are here](https://davidteather.github.io/proxyproviders/#proxyproviders.proxy_provider.ProxyConfig). In this example we will configure it to use a shorter `refresh_interval` than default.

```py
from proxyproviders import Webshare, ProxyConfig
import time

config = ProxyConfig(refresh_interval=3)
ws = Webshare(api_key="your-api-token", config=config)

proxies = ws.list_proxies() # calls API 

ws.list_proxies() # cached

time.sleep(5)
ws.list_proxies() # calls API since it's more than 3s later
```

### Function Using Generic ProxyProvider

Since all proxy providers implement the same interface, we can make a function that allows us to easily swap out and utilize different providers. This is the main appeal of having a unified interface. It allows other modules to be provider agnostic, like my [TikTokAPI](https://github.com/davidteather/TikTok-Api) package.

```py
from proxyproviders import Webshare, ProxyProvider, ProxyConfig

def some_function(provider: ProxyProvider):
    proxies = provider.list_proxies()
    print(proxies)

webshare = Webshare(api_key="your_api_key")
brightdata = BrightData(api_key="your_api_key", zone="my_zone")

some_function(webshare)
some_function(brightdata)
```

### Making Your Own Proxy Provider

Here's a skeleton of how you can make your very own `ProxyProvider` class. You'll need to implemenet all the required functions of the `ProxyProvider` which may be more than what's here at the time of writing.

If you do find yourself making one of these, consider contributing it back to the repository so everyone can use them :D

```py
from proxyproviders import ProxyProvider, ProxyConfig, Proxy
from typing import List, Optional

class MyProxyProvider(ProxyProvider):
    def __init__(self, config: Optional[ProxyConfig] = None):
        super().__init__(config=config)

    def _fetch_proxies(self):
        proxies: List[Proxy] = []

        for i in range(10):
            # TODO: your real proxy fetching logic

            # There are required fields on the Proxy class, be sure that these are filled out properly
            # especially if you're using it with another library.
            proxy = Proxy(
                id=str(i),
                username="username",
                password="password",
                proxy_address="192.168.1.1",
                port=80,
            )

            proxies.append(proxy)

        return proxies

def some_function(provider: ProxyProvider):
    proxies = provider.list_proxies()
    for proxy in proxies:
        print(proxy)

provider = MyProxyProvider()
some_function(provider) # calls the function with the provider
```

