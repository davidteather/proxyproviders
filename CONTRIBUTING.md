# Contributing to ProxyProviders

This guide shows you how to add new proxy providers and test them properly.

## Quick Start

1. **Fork and clone**: `git clone https://github.com/your-username/proxyproviders.git`
2. **Install**: `uv sync && uv tool install pre-commit && pre-commit install` ([install uv](https://docs.astral.sh/uv/getting-started/installation/) first)
3. **Test**: `uv run pytest tests/ --ignore=tests/integration -v`

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/), which manages the virtual environment and dependencies
- Git

## Linting and Type Checking

These run in CI and in the pre-commit hooks, and are configured in `pyproject.toml`.

```bash
uv run ruff check .          # lint, add --fix to apply safe fixes
uv run ruff format .         # format
uv run mypy                  # strict type checking of the package
```

## Running Tests

```bash
# Unit tests (fast)
uv run pytest tests/ --ignore=tests/integration -v

# Integration tests (need API keys set for each provider)
export RUN_INTEGRATION_TESTS=1 WEBSHARE_API_KEY="your-key" BRIGHTDATA_API_KEY="your-key"
uv run pytest tests/integration/ -v

# Check coverage (should be >95%)
uv run coverage run -m pytest tests/ --ignore=tests/integration
uv run coverage report --show-missing
```

## Adding a New Proxy Provider

New providers are very welcome. If you use Claude Code or another coding agent, the
`add-provider` skill in [.claude/skills/add-provider/SKILL.md](.claude/skills/add-provider/SKILL.md)
walks through the whole process step by step; in Claude Code, ask it to "add a provider
for <vendor>". The same file is a readable checklist if you are doing it by hand, and
[AGENTS.md](AGENTS.md) describes the codebase.

If you only want to use a vendor's proxies in your own project, you may not need a
provider at all: `ProxyList([...])` takes any list of proxies.

### 1. Email the maintainer first

Email David at **contact.davidteather@gmail.com** before or while you open the pull
request, with:

- the vendor's name and a link to its API documentation
- whether the vendor has an affiliate or referral program
- whether you can provide a test account or API key for integration tests
- whether you work for the vendor (welcome, just say so)

Two things depend on this. Links to the vendor in the docs go through the maintainer's
affiliate redirect, which is how the project is funded and is disclosed next to each
link. And integration tests only run with a repository secret the maintainer adds. Send
credentials by email only, never in an issue, pull request or commit.

### 2. Write the provider

Add `proxyproviders/providers/<vendor>.py` with a class that subclasses `ProxyProvider`
and returns `Proxy` objects from `_fetch_proxies`. Use `webshare.py` (a vendor with a
list API) or `brightdata.py` (a gateway vendor) as the model. The essentials:

- pass `timeout=self.config.timeout` to every HTTP call
- raise `ProxyFetchException`, `ProxyInvalidResponseException` or
  `ProxyConversionException`, not raw `requests` errors
- set `protocols` on each proxy (`["http", "https"]`, or `["socks5"]` for a SOCKS endpoint)
- type everything; `uv run mypy` is strict

Then export the class from `proxyproviders/__init__.py` and add it to `__all__`.

### 3. Unit tests

Create `tests/providers/test_<vendor>.py`, modelled on `test_webshare.py`. Mock the
vendor's API with `responses`; unit tests must not use the network. Cover success,
HTTP errors, timeouts, malformed responses and `get_proxy()`. Coverage must stay at or
above 95%.

### 4. Integration test

Create `tests/integration/test_<vendor>_integration.py`, skipped unless
`RUN_INTEGRATION_TESTS` and `<VENDOR>_API_KEY` are set, and add the secret name to the
`env:` block in `.github/workflows/ci-main.yml`.

Integration tests do not run on pull requests, because forks cannot read repository
secrets. They run on `main` after the merge. So run yours locally with a real key and
paste the output into the pull request:

```bash
RUN_INTEGRATION_TESTS=1 YOURVENDOR_API_KEY=... uv run pytest tests/integration/test_<vendor>_integration.py -v
```

### 5. Documentation

- `.sphinx/providers/<vendor>.rst`, plus a bullet and an include in `.sphinx/proxyproviders.rst`
- the providers table in `README.md`
- the provider list in `.sphinx/llms.txt`
- the class docstring: how to get credentials, every parameter, a working example

Link to the vendor's plain homepage and note in the pull request that the links are
placeholders. The maintainer swaps them for the affiliate links before merging. Please
do not use your own referral link.

## Submitting Changes

1. **Run tests**: `uv run pytest tests/ -v`
2. **Check coverage**: `uv run coverage run -m pytest tests/ --ignore=tests/integration && uv run coverage report`
3. **Pre-commit passes**: `pre-commit run --all-files`
4. **Create PR** with:
   - What provider you're adding
   - How to get API keys
   - Test coverage proof, and the output of your local integration test run
   - Whether you have emailed the maintainer about the affiliate link and a test key

**Requirements for PR approval:**
- Follows existing code patterns
- \>95% test coverage
- Unit + integration tests
- Clear documentation