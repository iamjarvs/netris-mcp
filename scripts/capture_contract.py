import json
import httpx
from pathlib import Path

BASE_URL = "https://adam-ctl.netris.io"
USER = "netris"
PASS = "913QGAi6oQTSGgZm20eU"

client = httpx.Client(base_url=BASE_URL, verify=False, timeout=15.0)

auth_res = client.post("/api/auth", json={"user": USER, "password": PASS, "auth_schema_key": "local"})
if auth_res.status_code != 200:
    raise RuntimeError(f"Auth failed: {auth_res.text}")

fixtures_dir = Path("tests/fixtures")
fixtures_dir.mkdir(parents=True, exist_ok=True)

SENSITIVE_KEYS = {"password", "bgppassword", "bgp_password", "secret", "token", "email"}

def sanitize(obj):
    if isinstance(obj, dict):
        return {
            k: ("***" if k.lower() in SENSITIVE_KEYS else sanitize(v))
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [sanitize(item) for item in obj[:20]]
    return obj

endpoints = {
    "sites": "/api/v2/sites",
    "tenants": "/api/tenants",
    "vpc": "/api/v2/vpc",
    "vpc_peering": "/api/v2/vpc-peering",
    "hardware": "/api/v2/hw",
    "hardware_profiles": "/api/v2/hw/profiles",
    "hardware_nos": "/api/v2/hw/nos",
    "hardware_ports": "/api/v2/hw/ports",
    "inventory_profiles": "/api/inventoryProfiles",
    "links": "/api/v2/link",
    "ports": "/api/v2/ports",
    "vnet": "/api/v2/vnet",
    "ipam": "/api/v2/ipam",
    "ebgp": "/api/v2/ebgp",
    "ebgp_routemaps": "/api/v2/ebgp/routemaps",
    "ebgp_objects": "/api/ebgpobjects",
    "acl": "/api/acl",
    "static_routes": "/api/routes",
    "nat": "/api/v2/nat",
    "l4lb": "/api/v2/l4lb",
    "dashboard_widgets": "/api/v2/dashboard/widgets",
    "dashboard_agent_heartbeats": "/api/v2/dashboard/agent-heartbeats",
    "dashboard_hardware_health": "/api/v2/dashboard/hardware-health",
    "dashboard_totalcounts": "/api/dashboard/totalcounts",
    "lookingglass_peers": "/api/lookingglass/peersList",
    "graphboards": "/api/graphboards",
    "dhcp_option_set": "/api/v2/dhcp-option-set",
    "license": "/api/v2/license",
}

for name, path in endpoints.items():
    res = client.get(path)
    if res.status_code == 200:
        raw = res.json()
        sanitized = sanitize(raw)
        out_file = fixtures_dir / f"{name}.json"
        with open(out_file, "w") as f:
            json.dump(sanitized, f, indent=2)
        print(f"Captured {name} -> {out_file}")
    else:
        print(f"Failed {name} ({path}): {res.status_code}")

print("Fixtures captured successfully.")
