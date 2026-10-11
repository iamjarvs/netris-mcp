# Netris Controller UI Survey Report

**Target Controller:** `https://adam-ctl.netris.io`  
**Authentication:** Authenticated as user `netris`  
**Survey Execution:** READ-ONLY inspection conducted on 2026-10-11  

---

## 1. Controller Version & System Information

- **Controller Version:** `4.15.0-011` (verified in `/settings/general`)
- **API Spec Versions:** Swagger / OpenAPI 3.0 supporting both `v1` and `v2` (`/api/docs/`)
- **License Type:** Enterprise (Non-production trial license)
  - **Expiration:** 2026-11-11 (*"Your license key expires in 30 days"*)
  - **Licensed Capacities:** Max Switches: 200, Max SoftGates: 8, Max Servers: 1024, Max DPUs: 0
- **System Configuration Parameters:**
  - **Controller FQDN:** `example.com`
  - **Controller Management IP:** `10.8.0.2`
  - **System ASN Range:** `4200000000 - 4209999999`
  - **Site Mesh VPN ASN Range:** `4210000000 - 4219999999`
  - **Wireguard Port Range:** `59000-60999`
  - **UFM Integration:** Reconcile interval 30s, Dry Run: false, Debug: false

---

## 2. Full Left-Hand Navigation Tree

The sidebar consists of 6 primary functional sections and a top logo redirecting to the main Dashboard:

1. **Dashboard** (`/`)
2. **Services**
   - V-Net (`/services/v-net`)
   - L4 Load Balancer (`/services/l4loadbalancer`)
   - ACL (`/services/acl`)
   - DHCP Options Sets (`/services/dhcp`)
   - ACL Port Groups (`/services/aclportgroups`)
   - Server Cluster (`/services/server-cluster`)
   - Server Cluster Template (`/services/server-cluster-template`)
3. **Network**
   - Inventory (`/net/inventory`)
   - IPAM (`/net/ipam`)
   - NAT (`/net/nat`)
   - E-BGP (`/net/ebgp`)
   - E-BGP Objects (`/net/ebgpobjects`)
   - E-BGP Route-maps (`/net/ebgproutemaps`)
   - Inventory Profiles (`/net/inventoryprofiles`)
   - Looking Glass (`/net/lookingglass`)
   - Network Interfaces (`/net/interfaces`)
   - Network Links (`/net/network-links`)
   - Routes (`/net/routes`)
   - Sites (`/net/sites`)
   - Topology (`/net/topology`)
   - VPC (`/net/vpc`)
   - VPC Peering (`/net/vpc-peering`)
4. **Accounts**
   - Users (`/accounts/users`)
   - Tenants (`/accounts/tenants`)
   - User Roles (`/accounts/userroles`)
   - Permission Groups (`/accounts/permissiongroups`)
5. **Telescope**
   - Graph Boards (`/telescope/trafficboards`)
   - API Logs (`/telescope/apilogs`)
   - Event Logs (`/telescope/eventlogs`)
   - Dashboard (`/`)
6. **API Docs** (`/api/docs`)
7. **Settings**
   - My Account (`/user/details`)
   - General (`/settings/general`)
   - License Key (`/settings/license-key`)
   - Login Whitelist (`/settings/whitelist`)
   - Authentication (`/settings/authentication`)
   - Monitoring Check Thresholds (`/settings/checks`)
   - Log Out (`/`)

---

## 3. Section Survey: Table Column Headers & Row Counts

| Category | Section / Page | Route | Table Column Headers | Row Count |
| :--- | :--- | :--- | :--- | :--- |
| **Telescope** | **Dashboard** | `/` | `Node Name`, `Heartbeat Status`, `Last Heartbeat Received`, `Site` | **76** rows (22 OK, 54 Critical) |
| **Services** | **V-Net** | `/services/v-net` | `V-Net`, `VPC`, `State`, `Gateways`, `Labels`, `Created Date`, `Modified Date` | **19** rows |
| **Services** | **L4 Load Balancer** | `/services/l4loadbalancer` | `Service name`, `VPC`, `Frontend`, `Status`, `Backends`, `Labels`, `Description`, `Site`, `Tenant`, `Created Date`, `Modified Date` | **0** rows |
| **Services** | **ACL** | `/services/acl` | `Name`, `VPC`, `Status`, `Action`, `Protocol`, `Source Address`, `Source Port`, `Destination Address`, `Destination Port` | **0** rows |
| **Services** | **DHCP Options Sets** | `/services/dhcp` | `Name`, `Default`, `Description`, `DHCP Options`, `Additional DHCP Options`, `Created Date`, `Modified Date` | **1** row (`Default`) |
| **Services** | **ACL Port Groups** | `/services/aclportgroups` | `Name`, `Status`, `Ports`, `Created Date`, `Modified Date` | **0** rows |
| **Services** | **Server Cluster** | `/services/server-cluster` | `Server Cluster`, `State`, `VPC`, `V-Nets`, `Gateways`, `Created Date`, `Modified Date` *(Nested: `Server`, `Shared Endpoint`)* | **5** rows (`ACME`, `Alpha-Workload-660663`, `Nokia`, `Rafay`, etc.) |
| **Services** | **Server Cluster Template** | `/services/server-cluster-template` | `Name`, `Created Date`, `Modified Date` *(Nested: JSON definitions)* | **3** rows (`datacenter-c-cluster-template`, `slurm-rocev2-fabric`, etc.) |
| **Network** | **Inventory** | `/net/inventory` | `Name`, `Description`, `Address`, `Health`, `Labels`, `Details`, `Usage`, `AS Number`, `Created Date`, `Modified Date` | **211** nodes |
| **Network** | **IPAM** | `/net/ipam` | `Prefix`, `Name`, `Type`, `VPC`, `Purpose`, `Utilization`, `Site`, `Global Routing`, `Tenant` | **22** prefixes |
| **Network** | **NAT** | `/net/nat` | `Name`, `VPC`, `Status`, `Action`, `Protocol`, `Source Address`, `Source Port`, `Destination Address`, `Destination Port`, `DNAT to IP`, `DNAT to Port`, `SNAT to IP` | **0** rows |
| **Network** | **E-BGP** | `/net/ebgp` | `Name`, `State`, `Details`, `VPC`, `Labels`, `Created Date`, `Modified Date` | **4** rows (`upstream1`–`upstream4`, all Established, AS 65401) |
| **Network** | **E-BGP Objects** | `/net/ebgpobjects` | `Name`, `Type`, `Value`, `Created date`, `Modified date` | **0** rows |
| **Network** | **E-BGP Route-maps** | `/net/ebgproutemaps` | `Name`, `Sequence Qty`, `Created date`, `Modified date` | **0** rows |
| **Network** | **Inventory Profiles** | `/net/inventoryprofiles` | `Name`, `Description`, `Accept SSH from`, `Accept custom services from`, `Services`, `Created Date`, `Modified Date` | **0** rows |
| **Network** | **Looking Glass** | `/net/lookingglass` | *Interactive Diagnostic Tool (No static table)*: Form controls: `VPC`, `Hardware`, `Family` (`IPv4`/`IPv6`), `Command` (`BGP Summary`, `BGP Route`, `Route`, `Traceroute`, `Ping`), `Source IP`, `Target IP` | N/A |
| **Network** | **Network Interfaces** | `/net/interfaces` | `Node`, `Interface`, `In Use`, `Description`, `Tenant`, `Status`, `Speed`, `Link Training`, `Transceiver`, `MTU`, `Site` | **7,110** interfaces |
| **Network** | **Network Links** | `/net/network-links` | Side A (`Node`, `Interface`, `Speed`, `IP Address`, `Status`), Side B (`Node`, `Interface`, `Speed`, `IP Address`, `Status`), `Utilization`, `Underlay` | **2,244** links |
| **Network** | **Routes** | `/net/routes` | `Prefix`, `Next-Hop`, `State`, `Site`, `VPC`, `Applied`, `Apply to`, `Description`, `Created Dates`, `Modified Date` | **0** rows |
| **Network** | **Sites** | `/net/sites` | `Name`, `Switch Fabric`, `Public ASN` | **2** rows (`Datacenter-A`: ASN 655001, `HardwareFree`: ASN 65501) |
| **Network** | **Topology** | `/net/topology` | *Interactive Canvas Visualization*: Filters by Site, EBGP, V-Net, Node, Expression, and Group by (`su`, `plane`, `rail`) | Fabric Graph Canvas |
| **Network** | **VPC** | `/net/vpc` | `VPC Id`, `Name`, `Admin Tenant`, `Labels`, `Created Date`, `Modified Date` | **11** rows (`Default`, `ACME`, `EMCA`, `Nokia`, `Rafay`, etc.) |
| **Network** | **VPC Peering** | `/net/vpc-peering` | `Name`, `VPC A`, `VPC B`, `Created Date`, `Modified Date` | **1** row (`Test VPC Peering` between ACME and EMCA) |
| **Accounts** | **Users** | `/accounts/users` | `Username`, `Full Name`, `User Role`, `Permission Group`, `Tenants`, `Details`, `Created Date`, `Modified Date` | **3** rows (`netris`, `readonly`, `system`) |
| **Accounts** | **Tenants** | `/accounts/tenants` | `Name`, `Description`, `Created Date` | **4** rows (`Admin`, `DemoTenant-Alpha`, `DemoTenant-Beta`, `DevOps`) |
| **Accounts** | **User Roles** | `/accounts/userroles` | `Name`, `Description`, `Permission Group`, `Tenants`, `Created Date`, `Modified Date` | **2** rows (`RO-User`, `RW-User`) |
| **Accounts** | **Permission Groups** | `/accounts/permissiongroups` | `Name`, `Description`, `Created Date`, `Modified Date` | **0** rows |
| **Telescope** | **Graph Boards** | `/telescope/trafficboards` | *Telemetry Dashboard*: Chart widgets for `tx95th`, `rx95th`, `tx/rx cur/min/max` bitrates with zoom synchronization | **1** board configured (`Datacenter-A Demo1@Admin`) |
| **Telescope** | **API Logs** | `/telescope/apilogs` | `URL`, `Name`, `User`, `Method`, `IP`, `Trace ID`, `Date` *(Expandable JSON request/response body)* | **4,255** entries |
| **Telescope** | **Event Logs** | `/telescope/eventlogs` | `Hardware`, `Status`, `Check Name`, `Message`, `Date` | **4** entries |
| **Settings** | **My Account** | `/user/details` | Form: `User Details`, `Notification Settings`, `Change Password` | N/A |
| **Settings** | **General** | `/settings/general` | Form: Version, Auth token, FQDN, Email, L4LB intervals, ASN ranges, Wireguard, UFM | N/A |
| **Settings** | **License Key** | `/settings/license-key` | Card: Enterprise license status, node allocation quotas, expiration date | **1** active license |
| **Settings** | **Login Whitelist** | `/settings/whitelist` | `Description`, `IP Address` | **2** rows (`ANY_IPv4 0.0.0.0/0`, `ANY_IPv6 ::/0`) |
| **Settings** | **Authentication** | `/settings/authentication` | `Name`, `Default`, `Status`, `Type` | **0** rows |
| **Settings** | **Monitoring Check Thresholds** | `/settings/checks` | `Check Name`, `Unit`, `Critical Low`, `Warning Low`, `Warning High`, `Critical High` | **14** threshold rules |

---

## 4. Dashboard Widgets, Alarm & Health Indicators

### Total Resources Card
- **Switches:** 68
- **SoftGates:** 8
- **Servers:** 135
- **VPCs:** 11
- **Clusters:** 5
- **Interfaces:** 7,110
- **Sites:** 2 (`Datacenter-A` and `HardwareFree`)
- **Links:** 2,244
- **V-Nets:** 19
- **ACLs:** 0

### Health & Alarm Indicators
- **Agent Heartbeats:** `22 OK`, `54 Critical` (Total: 76 nodes in heartbeat table)
  - Nodes with Critical heartbeat: unprovisioned/offline hardware-free plane switches (`sw-hardwarefree-plane*-leaf*`).
  - Nodes with OK heartbeat: live switches in Datacenter-A (`leaf-pod00-su*`, `ns-leaf-*`, `ns-softgate-*`).
- **Managed HW Health:** `2,854 OK`, `273 Warning`, `3 Critical` (Total: 3,130 sensor health checks).
- **External BGP:** `4 OK` (all 4 border sessions to upstream AS 65401 Established).
- **Controller Health:** `N/A`.
- **Top Bar Alerts:**
  - Notification badge: `22` events in "Last 24 hour".
  - License Banner: *"Your license key expires in 30 days."*

---

## 5. Fabric Troubleshooting Analysis

The controller exposes several purpose-built diagnostic interfaces that are critical for troubleshooting fabric operations:

1. **Looking Glass (`/net/lookingglass`):**
   - The primary command execution facility for live fabric diagnostics.
   - Allows operators to target specific switches/softgates within a VPC.
   - Available diagnostic routines:
     - `BGP Summary`: Queries local BGP daemon state, peer status, state duration, and prefix counts directly on switch/softgate hardware.
     - `BGP Route`: Inspects RIB/FIB BGP paths, communities, and next-hops for specific prefixes.
     - `Route`: Queries kernel routing tables on the selected node.
     - `Traceroute`: Executes hop-by-hop path tracing from selected source IP to target IPv4/IPv6 address.
     - `Ping`: Live ICMP connectivity verification from fabric interfaces.

2. **Topology (`/net/topology`):**
   - Interactive HTML5 canvas rendering the topology graph.
   - Highly geared towards AI/ML high-performance networks: supports **"Group by"** expressions such as `su` (scalable unit), `plane` (switching plane), and `rail` (GPU rail / RoCEv2 fabric).
   - Allows filtering by specific V-Net, E-BGP peer, Node, or regex/expression filter to isolate affected sub-fabrics.

3. **Network Links (`/net/network-links`):**
   - Central view of all 2,244 underlay and overlay links.
   - Shows dual endpoints (Side A node/port/IP vs. Side B node/port/IP), interface operational speeds, link statuses, and real-time **Utilization %**, enabling rapid detection of traffic blackholes, link flapping, or CRC/drop hotspots.

4. **Network Interfaces (`/net/interfaces`):**
   - Deep port-level telemetry across 7,110 interfaces.
   - Shows transceivers, MTU settings, link training status, administrative vs. operational state, and peer-derived port statistics.

5. **Telescope — Graph Boards (`/telescope/trafficboards`):**
   - Time-series throughput visualization.
   - Displays aggregated transit metrics (`tx95th`, `rx95th`, `tx cur/max/min`, `rx cur/max/min`) with synchronized zoom across multiple graphs. Preconfigured for `North-South — every spine port, summed`.

6. **Telescope — Event Logs & Monitoring Checks (`/telescope/eventlogs`, `/settings/checks`):**
   - Hardware sensor telemetry (`check_disk`, `check_load`, `check_port`, optical transceiver signal power in dBm for 1G/10G/25G/40G/100G).
   - Triggers warning/critical alarms when optical signal power drifts outside configured limits (e.g., -12 dBm to +4 dBm for 100G optics).

7. **Telescope — API Logs (`/telescope/apilogs`):**
   - 4,255 audit logs capturing every API invocation, HTTP method, client IP, Trace ID, and JSON request/response body. Essential for tracking state divergence between external automation / Terraform / Kubernetes operators and the controller.

---
*Note: The survey was performed completely READ-ONLY. No configuration changes, additions, deletions, or modifications were executed.*
