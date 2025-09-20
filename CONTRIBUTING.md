# Contributing to ProxyProviders

This guide shows you how to add new proxy providers and test them properly.

## Quick Start

1. **Fork and clone**: `git clone https://github.com/your-username/proxyproviders.git`
2. **Install**: `pip install -e . && pip install pre-commit && pre-commit install`
3. **Test**: `python -m pytest tests/ --ignore=tests/integration -v`

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git

## Running Tests

```bash
# Unit tests (fast)
python -m pytest tests/ --ignore=tests/integration -v

# Integration tests (need API keys set for each provider)
export RUN_INTEGRATION_TESTS=1 WEBSHARE_API_KEY="your-key" BRIGHTDATA_API_KEY="your-key"
python -m pytest tests/integration/ -v

# Check coverage (should be >95%)
python -m coverage run -m pytest tests/ --ignore=tests/integration
python -m coverage report --show-missing
```

## Adding a New Proxy Provider

If you're adding a new provider that isn't already in the library, here's a short guide to help you get started.

### 1. Create the Provider

Consider looking at `proxyproviders/providers/webshare.py` as an example. Your implemented provider will need to implement the `ProxyProvider` from `proxyproviders/proxy_provider.py`.

Here's a small scaffold that might be useful, however it may be outdated so check the `ProxyProvider` object for the latest required methods.

```python
class YourProvider(ProxyProvider):
    def __init__(self, api_key: str, config: Optional[ProxyConfig] = None):
        super().__init__(config)
        self.api_key = api_key

    def _fetch_proxies(self) -> List[Proxy]:
        # Call your provider's API and return List[Proxy]
        pass

    def _convert_to_proxy(self, data: Dict) -> Proxy:
        # Convert API response to Proxy object
        return Proxy(
            id=str(data["id"]),
            username=data["username"],
            password=data["password"],
            proxy_address=data["host"],
            port=int(data["port"]),
            # ... other fields
        )
```

### 2. Add to Package

Update `proxyproviders/__init__.py`:
```python
from .providers.your_provider import YourProvider
# Add "YourProvider" to __all__ list
```

## Writing Tests

### 3. Unit Tests

Create `tests/providers/test_your_provider.py` - feel free tocopy from `test_webshare.py` and modify it:

**Required tests:**
- Mock API success/error responses
- Test algorithm integration (`get_proxy()` works)
- Integration test with real API (if `YOUR_PROVIDER_API_KEY` env var set)

### 4. Integration Test

Create `tests/integration/test_your_provider_integration.py` - copy from existing integration tests.

## Submitting Changes

1. **Run tests**: `python -m pytest tests/ -v`
2. **Check coverage**: `python -m coverage run -m pytest tests/ --ignore=tests/integration && python -m coverage report`
3. **Pre-commit passes**: `pre-commit run --all-files`
4. **Create PR** with:
   - What provider you're adding
   - How to get API keys
   - Test coverage proof

**Requirements for PR approval:**
- Follows existing code patterns
- \>95% test coverage
- Unit + integration tests
- Clear documentation