from proxyproviders import Webshare, BrightData, ProxyProvider
import requests
import os


def request_with_proxy(provider: ProxyProvider):
    requests_proxy = None

    if provider:
        proxies = provider.list_proxies()

        requests_proxy = {
            "http": f"http://{proxies[0].username}:{proxies[0].password}@{proxies[0].proxy_address}:{proxies[0].port}",
            "https": f"http://{proxies[0].username}:{proxies[0].password}@{proxies[0].proxy_address}:{proxies[0].port}",
        }

    r = requests.get("https://httpbin.org/ip", proxies=requests_proxy)
    return r.json()


webshare = Webshare(api_key="your_api_key")
brightdata = BrightData(api_key="your_api_key", zone="your_zone")

print(f"Your IP: {request_with_proxy(None)}")
print(f"Webshare: {request_with_proxy(webshare)}")
print(f"BrightData: {request_with_proxy(brightdata)}")
