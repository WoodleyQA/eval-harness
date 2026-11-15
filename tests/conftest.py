"""Skip live-API tests when no key is configured, so a fresh clone runs clean."""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: calls the real Anthropic API (skipped without ANTHROPIC_API_KEY)"
    )


def pytest_collection_modifyitems(config, items):
    if os.getenv("ANTHROPIC_API_KEY"):
        return
    skip_live = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
