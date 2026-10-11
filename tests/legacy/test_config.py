"""
Tests for netris_mcp.config — environment variable loading and validation.
"""

import os
import pytest

from netris_mcp.config import get_config


def _set_required(host="netris.example.com", username="admin", password="secret"):
    os.environ["NETRIS_HOST"] = host
    os.environ["NETRIS_USERNAME"] = username
    os.environ["NETRIS_PASSWORD"] = password


def _clear_netris_env():
    for key in [
        "NETRIS_HOST", "NETRIS_USERNAME", "NETRIS_PASSWORD",
        "NETRIS_SSL_VERIFY", "NETRIS_SESSION_REFRESH", "NETRIS_TIMEOUT",
    ]:
        os.environ.pop(key, None)


@pytest.fixture(autouse=True)
def clean_env():
    _clear_netris_env()
    yield
    _clear_netris_env()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_get_config_returns_values():
    _set_required()
    cfg = get_config()
    assert cfg.host == "netris.example.com"
    assert cfg.username == "admin"
    assert cfg.password == "secret"


def test_get_config_defaults():
    _set_required()
    cfg = get_config()
    assert cfg.ssl_verify is True
    assert cfg.session_refresh_seconds == 1800
    assert cfg.timeout == 30.0


def test_ssl_verify_false():
    _set_required()
    os.environ["NETRIS_SSL_VERIFY"] = "false"
    cfg = get_config()
    assert cfg.ssl_verify is False


def test_ssl_verify_zero():
    _set_required()
    os.environ["NETRIS_SSL_VERIFY"] = "0"
    cfg = get_config()
    assert cfg.ssl_verify is False


def test_ssl_verify_true_explicit():
    _set_required()
    os.environ["NETRIS_SSL_VERIFY"] = "true"
    cfg = get_config()
    assert cfg.ssl_verify is True


def test_session_refresh_custom():
    _set_required()
    os.environ["NETRIS_SESSION_REFRESH"] = "600"
    cfg = get_config()
    assert cfg.session_refresh_seconds == 600


def test_timeout_custom():
    _set_required()
    os.environ["NETRIS_TIMEOUT"] = "60.5"
    cfg = get_config()
    assert cfg.timeout == 60.5


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


def test_missing_host_raises():
    os.environ["NETRIS_USERNAME"] = "admin"
    os.environ["NETRIS_PASSWORD"] = "secret"
    with pytest.raises(ValueError, match="NETRIS_HOST"):
        get_config()


def test_missing_username_raises():
    os.environ["NETRIS_HOST"] = "ctrl"
    os.environ["NETRIS_PASSWORD"] = "secret"
    with pytest.raises(ValueError, match="NETRIS_USERNAME"):
        get_config()


def test_missing_password_raises():
    os.environ["NETRIS_HOST"] = "ctrl"
    os.environ["NETRIS_USERNAME"] = "admin"
    with pytest.raises(ValueError, match="NETRIS_PASSWORD"):
        get_config()


def test_all_missing_raises_all_names():
    with pytest.raises(ValueError) as exc_info:
        get_config()
    msg = str(exc_info.value)
    assert "NETRIS_HOST" in msg
    assert "NETRIS_USERNAME" in msg
    assert "NETRIS_PASSWORD" in msg


def test_invalid_timeout_raises():
    _set_required()
    os.environ["NETRIS_TIMEOUT"] = "not-a-number"
    with pytest.raises(ValueError, match="NETRIS_TIMEOUT"):
        get_config()


def test_invalid_session_refresh_raises():
    _set_required()
    os.environ["NETRIS_SESSION_REFRESH"] = "abc"
    with pytest.raises(ValueError, match="NETRIS_SESSION_REFRESH"):
        get_config()


def test_session_refresh_minimum_enforced():
    _set_required()
    os.environ["NETRIS_SESSION_REFRESH"] = "5"
    cfg = get_config()
    assert cfg.session_refresh_seconds == 60
