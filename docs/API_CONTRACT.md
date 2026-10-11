# Netris Controller API Contract (Verified Live)

> Target: `https://adam-ctl.netris.io` (Netris Controller v4.x)
> Date Verified: 2026-10-11
> Auth Mechanism: `POST /api/auth` (`{"user": "...", "password": "...", "auth_schema_key": "local"}`) -> sets `connect.sid` cookie.
> Response Envelope: `{"data": ..., "isSuccess": true, "message": "", "errors": null, "meta": {"apiVersion": "v2", "statusCode": 200}}`

---

## 1. Verified Working Endpoints Matrix

| Resource Domain | API Path | Version | Lab Record Count | Envelope / Notes |
|---|---|---|---|---|
| **Sites** | `/api/v2/sites` | v2 | 2 sites | Standard envelope. Also `/api/sites` works. |
| **Tenants** | `/api/tenants` | v1 | 4 tenants | Standard envelope. **v1-only** (`/api/v2/tenant` returns 404). |
| **VPC** | `/api/v2/vpc` | v2 | 11 VPCs | Standard envelope. |
| **VPC Peering** | `/api/v2/vpc-peering` | v2 | 1 peering | Standard envelope. |
| **Hardware (Inventory)** | `/api/v2/hw` | v2 | 211 hardware devices | Full inventory. Filterable by type, site, tenant. |
| **Hardware Profiles** | `/api/v2/hw/profiles` | v2 | 8 profiles | Switch NOS/platform profiles. |
| **Hardware NOS** | `/api/v2/hw/nos` | v2 | 4 NOS options | Supported NOS list. |
| **Hardware Ports** | `/api/v2/hw/ports` | v2 | 1598 ports | Switch port mapping. |
| **Physical Links** | `/api/v2/link` | v2 | 2244 links | Paginated cable/interconnect topology. |
| **Switch Ports** | `/api/v2/ports` | v2 | 7110 interfaces | Full port inventory across fabric. |
| **V-Net (Overlay Networks)**| `/api/v2/vnet` | v2 | 19 V-Nets | **Crucial:** `/api/v2/vnet` works; `/api/v2/v-net` is 404! |
| **IPAM** | `/api/v2/ipam` | v2 | 11 allocations | Complete hierarchical tree of allocations and subnets. |
| **E-BGP Sessions** | `/api/v2/ebgp` | v2 | 4 sessions | BGP peering configs and states. |
| **E-BGP Route Maps** | `/api/v2/ebgp/routemaps` | v2 | 0 | Route map definitions. |
| **E-BGP Objects** | `/api/ebgpobjects` | v1 | 0 | **v1-only** prefix lists / match objects. |
| **Access Control Lists** | `/api/acl` | v1 | 0 | **v1-only** (`/api/v2/acl` is 404). |
| **Static Routes** | `/api/routes` | v1 | 0 | **v1-only** (`/api/v2/static-route` is 404). |
| **NAT Rules** | `/api/v2/nat` | v2 | 1 rule | Standard envelope. |
| **L4 Load Balancer** | `/api/v2/l4lb` | v2 | 0 | Standard envelope. |
| **Dashboard Widgets** | `/api/v2/dashboard/widgets` | v2 | 6 widgets | Aggregated telemetry & hardware status. |
| **Agent Heartbeats** | `/api/v2/dashboard/agent-heartbeats` | v2 | 50 agents | Health of running Netris daemons on switches. |
| **Hardware Health** | `/api/v2/dashboard/hardware-health` | v2 | 22 items | Alarms, status, resource usage. |
| **Dashboard Total Counts** | `/api/dashboard/totalcounts` | v1 | 10 metrics | Total counts for fast overview. |
| **Looking Glass** | `/api/lookingglass/peersList` | v1 | 4 peers | Real-time routing state from fabric switches. |
| **Graph Boards** | `/api/graphboards` | v1 | 2 boards | Telemetry dashboards. |
| **DHCP Option Sets** | `/api/v2/dhcp-option-set` | v2 | 1 set | DHCP server option definitions. |
| **License** | `/api/v2/license` | v2 | 1 license | Fabric license state. |

---

## 2. Corrections to Legacy `netris-mcp` Implementation

During live testing against the controller, several discrepancies in the initial repository (`iamjarvs/netris-mcp`) and documentation were uncovered:

1. **VNet Endpoint Path:**
   - *Legacy assumption:* `/api/v2/v-net/`
   - *Live Reality:* Returns **404**. The correct path is `/api/v2/vnet` (unhyphenated).

2. **Tenant Endpoint Version:**
   - *Legacy assumption:* `/api/v2/tenant/`
   - *Live Reality:* Returns **404**. Tenants are v1-only at `/api/tenants`.

3. **ACL Endpoint Version:**
   - *Legacy assumption:* `/api/v2/acl/`
   - *Live Reality:* Returns **404**. ACL is v1-only at `/api/acl`.

4. **Static Routes Endpoint Version:**
   - *Legacy assumption:* `/api/v2/static-route/`
   - *Live Reality:* Returns **404**. Static routing is v1-only at `/api/routes`.

5. **IPAM Subnet & Allocation Sub-paths:**
   - *Legacy assumption:* `/api/v2/ipam/subnet/` and `/api/v2/ipam/allocation/`
   - *Live Reality:* Returns **404**. The single `/api/v2/ipam` endpoint returns the entire tree of allocations and subnets hierarchically.

6. **Hardware/Switch Listing:**
   - *Legacy assumption:* `GET /api/v2/hw/switch/`
   - *Live Reality:* Returns empty object `{}`. The complete inventory of switches, softgates, and servers lives under `GET /api/v2/hw`.

7. **VPC Scoping Defaults:**
   - Queries to `/api/v2/ipam` and related network services default to the Default VPC unless `filterByVpc=all` or an explicit VPC ID is supplied.
