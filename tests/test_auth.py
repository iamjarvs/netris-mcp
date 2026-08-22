"""
Tests for netris_mcp.auth — login and session refresh.
Uses respx to mock httpx without a real server.
"""

import pytest
import respx
import httpx

from netris_mcp.auth import login, refresh_session


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_login_returns_cookies_on_success():
    respx.post("https://netris.example.com/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok"},
            headers={"Set-Cookie": "connect.sid=abc123; Path=/; HttpOnly"},
        )
    )
    cookies = await login("netris.example.com", "admin", "secret")
    assert "connect.sid" in cookies
    assert cookies["connect.sid"] == "abc123"


@pytest.mark.asyncio
@respx.mock
async def test_login_raises_on_401():
    respx.post("https://netris.example.com/api/v2/auth/login").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(RuntimeError, match="401"):
        await login("netris.example.com", "admin", "wrong-password")


@pytest.mark.asyncio
@respx.mock
async def test_login_raises_on_connect_error():
    respx.post("https://netris.example.com/api/v2/auth/login").mock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(RuntimeError, match="Cannot reach"):
        await login("netris.example.com", "admin", "secret")


@pytest.mark.asyncio
@respx.mock
async def test_login_raises_on_timeout():
    respx.post("https://netris.example.com/api/v2/auth/login").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    with pytest.raises(RuntimeError, match="Timed out"):
        await login("netris.example.com", "admin", "secret")


@pytest.mark.asyncio
@respx.mock
async def test_login_does_not_leak_password_in_error(caplog):
    """Password must not appear in error messages or logs."""
    respx.post("https://netris.example.com/api/v2/auth/login").mock(
        return_value=httpx.Response(401, text="bad credentials: secret")
    )
    with pytest.raises(RuntimeError) as exc_info:
        await login("netris.example.com", "admin", "secret")
    assert "secret" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# refresh_session()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_refresh_session_success():
    respx.get("https://netris.example.com/api/v2/auth/profile").mock(
        return_value=httpx.Response(200, json={"user": "admin"})
    )
    async with httpx.AsyncClient() as client:
        # Should not raise
        await refresh_session(client, "netris.example.com")


@pytest.mark.asyncio
@respx.mock
async def test_refresh_session_swallows_network_error():
    respx.get("https://netris.example.com/api/v2/auth/profile").mock(
        side_effect=httpx.ConnectError("refused")
    )
    async with httpx.AsyncClient() as client:
        # Must not raise — failure is swallowed as a warning
        await refresh_session(client, "netris.example.com")


@pytest.mark.asyncio
@respx.mock
async def test_refresh_session_swallows_timeout():
    respx.get("https://netris.example.com/api/v2/auth/profile").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    async with httpx.AsyncClient() as client:
        await refresh_session(client, "netris.example.com")


@pytest.mark.asyncio
@respx.mock
async def test_refresh_session_swallows_401():
    respx.get("https://netris.example.com/api/v2/auth/profile").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    async with httpx.AsyncClient() as client:
        # 401 should be logged as a warning, not raised
        await refresh_session(client, "netris.example.com")
