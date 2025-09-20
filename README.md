# ProxyProviders

The Unified Python Proxy API for managing proxies with support for BrightData, WebShare, and more.

 [![codecov](https://codecov.io/gh/davidteather/proxyproviders/graph/badge.svg?token=MZF0KP7YMA)](https://codecov.io/gh/davidteather/proxyproviders) [![Sponsor Me](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub)](https://github.com/sponsors/davidteather) [![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidteather/proxyproviders)](https://github.com/davidteather/proxyproviders/releases) [![GitHub](https://img.shields.io/github/license/davidteather/proxyproviders)](https://github.com/davidteather/proxyproviders/blob/main/LICENSE) [![Downloads](https://pepy.tech/badge/proxyproviders)](https://pypi.org/project/proxyproviders/) ![](https://visitor-badge.laobi.icu/badge?page_id=davidteather.proxyproviders) [![Support Server](https://img.shields.io/discord/783108952111579166.svg?color=7289da&logo=discord&style=flat-square)](https://discord.gg/yyPhbfma6f) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white&style=flat-square)](https://www.linkedin.com/in/davidteather/)

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

For simple usage, you can get a proxy and use it immediately:
```py
from proxyproviders import Webshare
import requests

provider = Webshare(api_key="your-api-key")

# Get a proxy (uses RoundRobin by default) and use it with requests
from proxyproviders.models.proxy import ProxyFormat

proxy = provider.get_proxy()
response = requests.get("https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS))
print(response.json())

# Or in one-line
response = requests.get("https://httpbin.org/ip", proxies=provider.get_proxy().format(ProxyFormat.REQUESTS))
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
from proxyproviders import Webshare, BrightData, ProxyProvider, ProxyConfig

def some_function(provider: ProxyProvider):
    proxies = provider.list_proxies()
    print(proxies)

webshare = Webshare(api_key="your_api_key")
brightdata = BrightData(api_key="your_api_key", zone="my_zone")

some_function(webshare)
some_function(brightdata)
```

Here's a more meaningful example that takes the `Proxy` class and uses it to create a python requests http proxy.

#### Simple Usage
```py
from proxyproviders import Webshare
from proxyproviders.algorithms import Random, RoundRobin
from proxyproviders.models.proxy import ProxyFormat
import requests

provider = Webshare(api_key="your_api_key")

# Get proxy using default RoundRobin and make request
proxy = provider.get_proxy()
response = requests.get("https://httpbin.org/ip", proxies=proxy.format(ProxyFormat.REQUESTS))

# Or in one-line
response = requests.get("https://httpbin.org/ip", proxies=provider.get_proxy().format(ProxyFormat.REQUESTS))
```

#### Built-in Algorithms
```py
from proxyproviders import Webshare
from proxyproviders.algorithms import Random, RoundRobin, First

provider = Webshare(api_key="your_api_key")

# Default: RoundRobin (cycles through proxies for load balancing)
proxy = provider.get_proxy()

# Random selection
proxy = provider.get_proxy(Random())

# Always first proxy (deterministic)
proxy = provider.get_proxy(First())

# Algorithm can maintain state when reused
round_robin = RoundRobin()
proxy1 = provider.get_proxy(round_robin)
proxy2 = provider.get_proxy(round_robin)  # Next in sequence
```

#### Algorithm State Management
```py
from proxyproviders import Webshare
from proxyproviders.algorithms import RoundRobin, Random

provider = Webshare(api_key="your_api_key")

# Create reusable algorithm for state management
round_robin = RoundRobin()  # Maintains state across calls
random_algo = Random()      # Stateless but reusable

# Each call to round_robin will cycle to next proxy
for i in range(3):
    proxy = provider.get_proxy(round_robin)
    print(f"RoundRobin {i}: {proxy.proxy_address}")

# Provider also maintains its own default RoundRobin state when not specified
for i in range(3):
    proxy = provider.get_proxy()  # Uses provider's default RoundRobin
    print(f"Default {i}: {proxy.proxy_address}")
```

#### Custom Algorithms
```py
from proxyproviders.algorithms import Algorithm
from typing import List
from proxyproviders.models.proxy import Proxy

class USProxyAlgorithm(Algorithm):
    """Prefers US proxies, falls back to first available."""

    def select(self, proxies: List[Proxy]) -> Proxy:
        # Try to find a US proxy
        for proxy in proxies:
            if proxy.country_code == "US":
                return proxy
        # Fall back to first proxy
        return proxies[0]

# Use your custom algorithm
proxy = provider.get_proxy(USProxyAlgorithm())
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

