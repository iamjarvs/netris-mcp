# Instructions for LLMs using Netris MCP Server

This server provides tools to inspect and operate the Netris Network Controller (v4.15+) and managed AI fabric infrastructure.

## 1. AI Fabric Architecture Context
Netris is purpose-built to orchestrate and manage modern AI data centre fabrics, which operate across distinct network planes:
- **Front-End / North-South Network:** Multi-tenant Ethernet leaf-spine fabrics providing client ingress, Kubernetes control planes, cluster management, Out-of-Band (OOB) networks, and high-throughput storage (NFS/Ceph/WEKA/VAST). Managed natively via Netris VPCs, V-Net overlays (L2VPN/L3VPN), hardware NAT, and SoftGate L4 load balancers.
- **Back-End / East-West Accelerator Network:** Non-blocking, ultra-low-latency fabric connecting GPUs for distributed collective training and inference:
  - **InfiniBand:** Managed via the **NVIDIA UFM (Unified Fabric Manager)** integration plugin in Netris. Multi-tenancy is declared via `Server-Cluster` objects, which Netris maps to UFM PKeys (Partitions), port GUID memberships, and SHARP reduction trees.
  - **RoCEv2 Ethernet:** Rail-optimised Ethernet fabrics (e.g., NVIDIA Spectrum-X) configured with PFC (Priority Flow Control), ECN, and Adaptive Routing.
- **Scale-Up Rack Interconnect (NVIDIA NVLink NVL72):** Rack-scale GB200/GB300 domains interconnecting 72 GPUs across 9 NVLink switch trays. Netris taps into NVIDIA NMX Controller (NMX-C) over gRPC with mTLS to enforce NVLink partition boundaries matching `Server-Cluster` tenant definitions.
- **On-Host Networking (ROH & Host Agents):** Routing On the Host (ROH) runs BGP unnumbered / EVPN directly on bare-metal hosts and NVIDIA BlueField DPUs, advertising host loopbacks into top-of-rack switches and eliminating layer-2 broadcast domains.

## 2. General Operational Guidance
- Always explore fabric state prior to diagnosing issues or performing changes.
- Start with high-level umbrella tools before querying granular tables:
  1. `fabric_inventory(domain='summary')` to understand site, hardware, VPC, and tenant counts.
  2. `fabric_health(scope='overview')` to evaluate alarms, critical heartbeats, and border BGP states.
  3. `triage(symptom=...)` to execute targeted diagnostic playbooks (e.g. `vnet_degraded`, `bgp_session_down`).
  4. `architecture_reference(platform=...)` to pull operational guidance for Cumulus, SONiC, Junos, Arista, Nokia, or `ai_fabric`, `nvidia_ufm`, `nvidia_nvlink_nvl72`, `on_host_networking`.

## 3. Switch Command Execution & Addressing Conventions
- Use `run_switch_command(switch_name_or_ip=..., command=...)` to execute safe, read-only show commands on switches via the controller jump host.
- **Automatic Target Resolution:** The tool automatically resolves:
  - Switch hostnames (e.g. `leaf-pod00-su1-r1`, `spine-0-pod00`, `ns-leaf-0`) to their out-of-band management IP (`mgmtAddress`).
  - In-band routing loopbacks (`mainAddress` e.g. `10.253.128.6`) redirected to the reachable management IP (`10.253.0.6`).
- **Addressing Distinction:**
  - `mgmtAddress` is the out-of-band management IP reachable by SSH from the jump host.
  - `mainAddress` is the internal underlay / BGP loopback IP (not bound to SSH).

## 4. Audit & Event Logs
- Use `fabric_audit(category='api_logs')` to query the controller's comprehensive REST API audit trail (capturing who changed what, when, method, URL, and client IP).
- If querying `fabric_audit(category='events')` in environments where hardware sensor event logging is unconfigured, the tool gracefully returns recent configuration mutation audit events.
- Use `fabric_audit(category='monitoring_checks')` to inspect optical transceiver and hardware threshold rules.

## 5. Safety and Mutations
- The server runs in **read-only** mode by default.
- Any mutating tool requires `dry_run=False` and `NETRIS_MCP_MODE=read-write` configured on the host. Always inspect the returned dry-run diff preview before advising commit operations.
