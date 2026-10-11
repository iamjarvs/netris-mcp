"""
Tests for netris_mcp.client — URL builder and HTTP verb helpers.
Uses respx to mock httpx without a real server.
"""

import pytest
import respx
import httpx

from netris_mcp.client import api_url, get, post, put, delete


# ---------------------------------------------------------------------------
# api_url
# ---------------------------------------------------------------------------


def test_api_url_collection():
    assert api_url("https://ctrl.example.com", "vpc") == "https://ctrl.example.com/api/v2/vpc/"


def test_api_url_item():
    assert api_url("https://ctrl.example.com", "vpc", 42) == "https://ctrl.example.com/api/v2/vpc/42"


def test_api_url_strips_trailing_slash_from_base():
    assert api_url("https://ctrl.example.com/", "vpc") == "https://ctrl.example.com/api/v2/vpc/"


def test_api_url_strips_slash_from_resource():
    assert api_url("https://ctrl.example.com", "/vpc/") == "https://ctrl.example.com/api/v2/vpc/"


def test_api_url_zero_id():
    assert api_url("https://ctrl.example.com", "vpc", 0) == "https://ctrl.example.com/api/v2/vpc/0"


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_returns_json():
    respx.get("https://ctrl.example.com/api/v2/vpc/").mock(
        return_value=httpx.Response(200, json={"data": [{"id": 1, "name": "test-vpc"}]})
    )
    async with httpx.AsyncClient() as client:
        result = await get(client, "https://ctrl.example.com/api/v2/vpc/")
    assert result == {"data": [{"id": 1, "name": "test-vpc"}]}


@pytest.mark.asyncio
@respx.mock
async def test_get_raises_on_404():
    respx.get("https://ctrl.example.com/api/v2/vpc/99").mock(
        return_value=httpx.Response(404, text="Not found")
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="404"):
            await get(client, "https://ctrl.example.com/api/v2/vpc/99")


@pytest.mark.asyncio
@respx.mock
async def test_get_raises_on_network_error():
    respx.get("https://ctrl.example.com/api/v2/vpc/").mock(
        side_effect=httpx.ConnectError("refused")
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="GET.*failed"):
            await get(client, "https://ctrl.example.com/api/v2/vpc/")


# ---------------------------------------------------------------------------
# post
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_post_returns_json():
    respx.post("https://ctrl.example.com/api/v2/vpc/").mock(
        return_value=httpx.Response(201, json={"id": 5, "name": "new-vpc"})
    )
    async with httpx.AsyncClient() as client:
        result = await post(client, "https://ctrl.example.com/api/v2/vpc/", {"name": "new-vpc"})
    assert result["id"] == 5


@pytest.mark.asyncio
@respx.mock
async def test_post_raises_on_422():
    respx.post("https://ctrl.example.com/api/v2/vpc/").mock(
        return_value=httpx.Response(422, text="Validation error")
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="422"):
            await post(client, "https://ctrl.example.com/api/v2/vpc/", {"name": ""})


# ---------------------------------------------------------------------------
# put
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_put_returns_json():
    respx.put("https://ctrl.example.com/api/v2/vpc/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "updated-vpc"})
    )
    async with httpx.AsyncClient() as client:
        result = await put(client, "https://ctrl.example.com/api/v2/vpc/5", {"name": "updated-vpc"})
    assert result["name"] == "updated-vpc"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_delete_returns_empty_dict_on_204():
    respx.delete("https://ctrl.example.com/api/v2/vpc/5").mock(
        return_value=httpx.Response(204)
    )
    async with httpx.AsyncClient() as client:
        result = await delete(client, "https://ctrl.example.com/api/v2/vpc/5")
    assert result == {}


@pytest.mark.asyncio
@respx.mock
async def test_delete_raises_on_403():
    respx.delete("https://ctrl.example.com/api/v2/vpc/5").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="403"):
            await delete(client, "https://ctrl.example.com/api/v2/vpc/5")
