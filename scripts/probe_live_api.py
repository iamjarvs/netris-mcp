import os
import json
import httpx

BASE_URL = "https://adam-ctl.netris.io"
USER = "netris"
PASS = "913QGAi6oQTSGgZm20eU"

client = httpx.Client(base_url=BASE_URL, verify=False, timeout=15.0)

# 1. Login
auth_res = client.post("/api/auth", json={"user": USER, "password": PASS, "auth_schema_key": "local"})
print(f"Auth status: {auth_res.status_code}")
if auth_res.status_code != 200:
    print("Auth failed:", auth_res.text)
    exit(1)

# List of endpoints to probe (both v1 and v2 candidates)
candidates = [
    # Sites / Topology
    ("v2", "/api/v2/sites"),
    ("v1", "/api/sites"),
    ("v2", "/api/v2/topology/path"),
    
    # Tenants
    ("v1", "/api/tenants"),
    ("v2", "/api/v2/tenant"),
    ("v2", "/api/v2/tenants"),
    
    # VPC & Peering
    ("v2", "/api/v2/vpc"),
    ("v2", "/api/v2/vpc-peering"),
    ("unprefixed", "/vpc-peering"),
    
    # Hardware / Inventory
    ("v2", "/api/v2/hw"),
    ("v2", "/api/v2/hw/switch"),
    ("v2", "/api/v2/hw/softgate"),
    ("v2", "/api/v2/hw/controller"),
    ("v2", "/api/v2/hw/profiles"),
    ("v2", "/api/v2/hw/nos"),
    ("v2", "/api/v2/hw/ports"),
    ("v1", "/api/inventoryProfiles"),
    ("v1", "/api/dashboard/hw"),
    
    # Links & Interfaces
    ("v2", "/api/v2/link"),
    ("v2", "/api/v2/ports"),
    
    # VNet & Overlay
    ("v2", "/api/v2/vnet"),
    ("v2", "/api/v2/v-net"),
    ("v2", "/api/v2/vnet/unmanaged"),
    
    # IPAM
    ("v2", "/api/v2/ipam"),
    ("v2", "/api/v2/ipam/allocation"),
    ("v2", "/api/v2/ipam/subnet"),
    
    # BGP
    ("v2", "/api/v2/ebgp"),
    ("v2", "/api/v2/ebgp/routemaps"),
    ("v1", "/api/ebgpobjects"),
    ("v1", "/api/ebgproutemaps"),
    
    # ACL & Routing
    ("v1", "/api/acl"),
    ("v2", "/api/v2/acl"),
    ("v1", "/api/routes"),
    ("v2", "/api/v2/static-route"),
    
    # NAT & L4LB
    ("v2", "/api/v2/nat"),
    ("v2", "/api/v2/l4lb"),
    
    # Observability & Diagnostics
    ("v2", "/api/v2/dashboard/widgets"),
    ("v2", "/api/v2/dashboard/agent-heartbeats"),
    ("v2", "/api/v2/dashboard/hardware-health"),
    ("v1", "/api/dashboard/totalcounts"),
    ("v1", "/api/dashboard/hardwarealarms"),
    ("v1", "/api/apilogs"),
    ("v1", "/api/eventlogs"),
    ("v1", "/api/lookingglass/peersList"),
    ("v1", "/api/graphboards"),
    ("v2", "/api/v2/dhcp-option-set"),
    ("v2", "/api/v2/license"),
]

results = []

for tag, ep in candidates:
    try:
        res = client.get(ep)
        status = res.status_code
        try:
            body = res.json()
            is_success = body.get("isSuccess", True) if isinstance(body, dict) else True
            data = body.get("data") if isinstance(body, dict) else body
            item_count = len(data) if isinstance(data, (list, dict)) else (1 if data is not None else 0)
        except Exception:
            body = res.text[:100]
            is_success = False
            item_count = 0
            
        results.append({
            "tag": tag,
            "endpoint": ep,
            "status": status,
            "isSuccess": is_success,
            "count": item_count,
            "sample_snippet": str(body)[:120] if status == 200 else ""
        })
        print(f"[{status}] {ep} -> count: {item_count} (isSuccess: {is_success})")
    except Exception as e:
        print(f"[ERR] {ep} -> {e}")

with open("docs/live_probe_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nFinished probe! Saved to docs/live_probe_results.json")
