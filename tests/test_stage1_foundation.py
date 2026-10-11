import pytest
import respx
import httpx
from app.config import get_config, NetrisConfig
from app.netris_client import NetrisClient, NetrisAPIError, redact

def test_config_loader(tmp_path):
    cfg = get_config(root_dir=tmp_path)
    assert isinstance(cfg, NetrisConfig)
    assert cfg.mode in ("read-only", "read-write")
    assert cfg.port == 8750
    # Secrets should not be exposed in repr
    assert "913QGAi6oQTSGgZm20eU" not in repr(cfg)

def test_redact_helper():
    data = {"user": "netris", "password": "secret_password", "nested": {"bgp_password": "bgp123", "vlan": 10}}
    sanitized = redact(data)
    assert sanitized["password"] == "***"
    assert sanitized["nested"]["bgp_password"] == "***"
    assert sanitized["nested"]["vlan"] == 10

@pytest.mark.asyncio
@respx.mock
async def test_netris_client_auth_success():
    respx.post("https://test.netris.io/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {"user": "netris"}})
    )
    client = NetrisClient(base_url="https://test.netris.io", username="netris", password="pwd")
    ok = await client.login()
    assert ok is True
    await client.close()

@pytest.mark.asyncio
@respx.mock
async def test_netris_client_envelope_error():
    respx.post("https://test.netris.io/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    respx.get("https://test.netris.io/api/v2/sites").mock(
        return_value=httpx.Response(200, json={"isSuccess": False, "message": "Failed query", "errors": {"site": "invalid"}})
    )
    client = NetrisClient(base_url="https://test.netris.io", username="netris", password="pwd")
    with pytest.raises(NetrisAPIError) as exc_info:
        await client.get("/api/v2/sites")
    assert "Failed query" in str(exc_info.value)
    await client.close()

@pytest.mark.asyncio
@respx.mock
async def test_netris_client_401_reauth():
    auth_route = respx.post("https://test.netris.io/api/auth").mock(
        return_value=httpx.Response(200, json={"isSuccess": True, "data": {}})
    )
    # First call returns 401, second call returns 200
    respx.get("https://test.netris.io/api/v2/vpc").mock(
        side_effect=[
            httpx.Response(401, text="Unauthorized"),
            httpx.Response(200, json={"isSuccess": True, "data": [{"id": 1, "name": "Default"}]}),
        ]
    )
    client = NetrisClient(base_url="https://test.netris.io", username="netris", password="pwd")
    data = await client.get("/api/v2/vpc")
    assert len(data) == 1
    assert data[0]["name"] == "Default"
    assert auth_route.call_count >= 1
    await client.close()
