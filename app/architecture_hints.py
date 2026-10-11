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
