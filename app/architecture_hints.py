"""Network Architecture & Multi-Vendor NOS Reference Hints.

Provides platform context, CLI command syntax hints, and troubleshooting patterns across:
- NVIDIA Cumulus Linux 5.x (NVUE & FRRouting / vtysh)
- SONiC (Enterprise SONiC / Broadcom / NextHop / Dell / Edgecore)
- Arista EOS
- Nokia SR Linux (EDA / srl-cli)
- Juniper Junos OS (QFX / PTX EVPN-VXLAN)
"""

from __future__ import annotations

from typing import Any

NOS_ARCHITECTURES = {
    "ai_fabric": {
        "domain": "AI Cloud Data Centre Fabric Architecture",
        "overview": (
            "Modern AI clusters operate two distinct network planes: Front-End (North-South/Management/Storage) "
            "and Back-End (East-West/Scale-Out Compute), complemented by Scale-Up rack domains (NVLink NVL72) and on-host networking."
        ),
        "frontend_network": {
            "purpose": "Client ingress, Kubernetes control plane, cluster management, Out-of-Band (OOB), and high-throughput storage (NFS/Ceph/WEKA/VAST).",
            "technology": "Ethernet leaf-spine topology orchestrated natively by Netris using EVPN-VXLAN, VPC multi-tenancy, V-Net overlays (L2VPN/L3VPN), hardware NAT, and SoftGate L4 load balancers.",
            "addressing": "Dual-plane addressing: Out-of-Band management IPs (mgmtAddress) for control plane/SSH jump host access, and in-band underlay/routing loopbacks (mainAddress).",
        },
        "backend_network": {
            "purpose": "Non-blocking, ultra-low-latency East-West accelerator interconnect for GPU-to-GPU collective operations (AllReduce, All-to-All).",
            "infiniband_path": "Quantum-2 switches managed via the NVIDIA UFM (Unified Fabric Manager) integration plugin in Netris. Netris automates GUID discovery and PKey partition isolation declaratively per Server-Cluster.",
            "rocev2_ethernet_path": "High-performance Ethernet (e.g., NVIDIA Spectrum-X) configured in rail-optimised planes with PFC (802.1Qbb Priority Flow Control), ECN (Explicit Congestion Notification), ETS, and Adaptive Routing.",
        },
        "scale_up_fabric": {
            "name": "NVIDIA NVLink NVL72 / Multi-Node NVLink",
            "technology": "Rack-scale GB200/GB300 NVL72 architectures interconnecting 72 GPUs across 9 NVLink switch trays in a full mesh.",
            "netris_role": "Netris links into NVIDIA NMX Controller (NMX-C) via gRPC with mTLS, declaratively enforcing NVLink partitions based on Server-Cluster tenant boundaries to prevent cross-tenant GPU leakage.",
        },
        "on_host_networking": {
            "technology": "Routing On the Host (ROH) running BGP/EVPN directly on host OS or NVIDIA BlueField DPUs, advertising host loopbacks into top-of-rack switches.",
            "acceleration": "Multi-rail NIC striping, SR-IOV, GPUDirect RDMA, and PXN (PCIe Acceleration) offloads.",
        },
        "key_show_commands": [
            "nv show router bgp",
            "sudo vtysh -c 'show bgp summary'",
            "sudo vtysh -c 'show evpn vni'",
            "roce_sys -s",
            "ibstat",
            "ibdiagnet",
        ],
        "troubleshooting_hints": [
            "In Netris CloudSim / production environments, target switches via out-of-band management IP (mgmtAddress), not underlay loopback (mainAddress).",
            "Server multi-tenancy across Ethernet, InfiniBand (PKeys), and NVLink (partitions) is consolidated declaratively into the Netris Server-Cluster object.",
            "Monitor PFC pause frames and buffer occupancy to detect RoCEv2 incast congestion hotspots.",
        ],
    },
    "nvidia_ufm": {
        "vendor": "NVIDIA Networking",
        "technology": "Unified Fabric Manager (UFM) for InfiniBand fabrics",
        "netris_integration": (
            "The Netris-UFM plugin automates InfiniBand tenant isolation by mapping Netris Server-Cluster objects "
            "to UFM PKeys (Partitions), port GUID memberships, and optional SHARP (Scalable Hierarchical Aggregation and Reduction Protocol) trees."
        ),
        "configuration_prerequisites": [
            "UFM gv.cfg must set 'default_membership = limited' under [MngNetwork] to permit programmatic REST API partition enforcement.",
            "Netris Controller discovers port GUIDs and synchronises tenant PKey boundaries continuously.",
        ],
        "key_show_commands": [
            "ibstat",
            "ibstatus",
            "sminfo",
            "perfquery",
            "ibdiagnet --sc",
        ],
        "troubleshooting_hints": [
            "Verify UFM REST API health and token credentials configured in Netris Settings -> General.",
            "Ensure compute nodes assigned to a tenant share matching InfiniBand PKeys to allow collective communication.",
            "Check for fabric-wide SM (Subnet Manager) master election conflicts using 'sminfo'.",
        ],
    },
    "nvidia_nvlink_nvl72": {
        "vendor": "NVIDIA",
        "technology": "NVLink Multi-Node NVL72 / NMX Controller (NMX-C)",
        "netris_integration": (
            "Netris integrates with NVIDIA NMX-C over gRPC with mTLS to synchronise NVLink partitions across 72-GPU rack domains (GB200/GB300). "
            "Eliminates manual GPU UID ledger tracking by reconciling partitions against declared Server-Cluster assignments every 10 seconds."
        ),
        "architecture_details": [
            "18 compute servers (72 GPUs total) interconnected by 9 NVLink switch trays in a full mesh.",
            "NMX-C runs locally per rack on an NVLink switch tray.",
            "Netris provides the single declarative source of truth for multi-tenant boundaries across Ethernet, InfiniBand, and NVLink.",
        ],
        "troubleshooting_hints": [
            "Verify GPU inventory ledger mapping server hostnames to GPU UIDs.",
            "Check mTLS client certificates and CA trust chain for NMX-C gRPC communication.",
            "Confirm that compute nodes in the same Server-Cluster reside in the same NVL partition.",
        ],
    },
    "on_host_networking": {
        "technology": "Routing On the Host (ROH) & Host Networking Agents",
        "overview": (
            "Netris extends cloud networking onto bare-metal hosts and hypervisors via Routing On the Host (ROH) and netris-agent, "
            "eliminating layer-2 VLAN sprawl and bridging overhead."
        ),
        "components": [
            "ROH: Host runs BGP unnumbered / EVPN to advertise its /32 loopbacks directly to ToR switches.",
            "DPU Offload: NVIDIA BlueField-2/3 DPUs running ovs-doca or embedded Linux offloading overlay encapsulation.",
            "Multi-Rail: GPU clusters bind dedicated ConnectX HCAs/NICs per rail for deterministic non-blocking communication.",
        ],
        "key_show_commands": [
            "ip -br addr",
            "ip route show",
            "systemctl status netris-agent",
            "rdma link",
            "ethtool -S <interface>",
        ],
        "troubleshooting_hints": [
            "Ensure netris-agent daemon is active: 'systemctl status netris-agent'.",
            "Verify BGP peering status between host loopback and leaf switch: 'ip route show proto bgp'.",
            "For RoCE workloads, verify MTU 9000 (jumbo frames) across all host and switch physical interfaces.",
        ],
    },
    "cumulus": {
        "vendor": "NVIDIA",
        "os_name": "Cumulus Linux 5.x",
        "control_plane": "FRRouting (FRR) daemons via vtysh and NVUE (NVIDIA User Experience)",
        "dataplane": "Linux switchdev kernel drivers offloading to Mellanox/NVIDIA Spectrum-2/3/4 ASICs",
        "key_show_commands": [
            "nv show system version",
            "nv show interface",
            "nv show router bgp",
            "sudo vtysh -c 'show bgp summary'",
            "sudo vtysh -c 'show evpn vni'",
            "sudo vtysh -c 'show ip route'",
            "ip -br link",
        ],
        "troubleshooting_hints": [
            "Netris switch agent runs as a systemd service: 'systemctl status netris-agent'.",
            "BGP EVPN is orchestrated natively in FRR; verify VNI tunnel status using 'vtysh -c \"show evpn vni\"'.",
            "NVUE provides declarative operational views: use 'nv show router bgp' for clean status tables.",
            "Always prepend 'sudo' when executing vtysh commands on Cumulus.",
            "Always target switches using out-of-band management IP (mgmtAddress) over SSH jump host.",
        ],
    },
    "sonic": {
        "vendor": "Open Compute Project / Broadcom / NextHop / Dell",
        "os_name": "Enterprise & Community SONiC",
        "control_plane": "Containerised microservices (SWSS, Syncd, BGP/FRR container)",
        "dataplane": "SAI (Switch Abstraction Interface) over Broadcom Tomahawk/Trident ASICs",
        "key_show_commands": [
            "show version",
            "show interfaces status",
            "show ip bgp summary",
            "show vxlan vnet",
            "show bfd summary",
        ],
        "troubleshooting_hints": [
            "BGP runs inside the 'bgp' docker container; direct vtysh access via 'docker exec -it bgp vtysh'.",
            "SAI programming status can be verified with 'show platform' and redis-dump inspects.",
        ],
    },
    "junos": {
        "vendor": "Juniper Networks",
        "os_name": "Junos OS / Junos Evolved",
        "control_plane": "Routing Protocol Daemon (rpd)",
        "dataplane": "Junos Packet Forwarding Engine (PFE / Trio / Express / Broadcom)",
        "key_show_commands": [
            "show version",
            "show interfaces terse",
            "show bgp summary",
            "show evpn instance",
            "show ethernet-switching table",
            "show route table <vrf-name>",
        ],
        "troubleshooting_hints": [
            "In Netris multi-vendor EVPN overlays, ensure target AS numbers match the site public/fabric ASN.",
            "Verify EVPN Type-2 (MAC/IP) and Type-5 (IP Prefix) routes with 'show route table bgp.evpn.0'.",
        ],
    },
    "nokia_sr_linux": {
        "vendor": "Nokia",
        "os_name": "SR Linux",
        "control_plane": "Microservices Linux architecture based on gNMI, state pub/sub, and NDK",
        "dataplane": "FP4/FP5 or merchant silicon via XDP/SRL drivers",
        "key_show_commands": [
            "show version",
            "show interface brief",
            "show network-instance default protocols bgp summary",
            "show network-instance <name> route-table",
        ],
        "troubleshooting_hints": [
            "SR Linux organises VRFs and overlays into 'network-instance' abstractions.",
            "Telemetry and configuration are native gNMI/YANG first.",
        ],
    },
    "arista_eos": {
        "vendor": "Arista Networks",
        "os_name": "EOS (Extensible Operating System)",
        "control_plane": "Sysdb state engine with multi-process daemons",
        "dataplane": "Hardware offload across StrataXGS / Jericho / Tomahawk",
        "key_show_commands": [
            "show version",
            "show interfaces status",
            "show ip bgp summary",
            "show vxlan vni",
            "show mac address-table",
        ],
        "troubleshooting_hints": [
            "Inspect VXLAN VTEP reachability with 'show vxlan address-table'.",
            "Verify overlay routing between MLAG leaf pairs via 'show ip route vrf <vrf>'.",
        ],
    },
}


def get_architecture_hint(platform: str) -> dict[str, Any]:
    """Retrieve operational hints and diagnostic commands for a network platform."""
    plat_key = platform.lower().replace(" ", "_").replace("-", "_")
    for key, data in NOS_ARCHITECTURES.items():
        if key in plat_key or plat_key in key:
            return data
    return {
        "note": f"Platform '{platform}' not explicitly indexed. Standard Linux/FRR patterns apply.",
        "common_commands": ["show version", "show ip bgp summary", "ip route show"],
    }
