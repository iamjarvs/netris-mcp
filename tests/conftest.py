"""
Shared pytest fixtures and configuration.
"""

import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def set_netris_env():
    """Set minimal Netris env vars for the test session if unset."""
    if not os.path.exists(".env"):
        os.environ.setdefault("NETRIS_HOST", "test.example.com")
        os.environ.setdefault("NETRIS_USERNAME", "test-user")
        os.environ.setdefault("NETRIS_PASSWORD", "test-password")
