from ..server import mcp


@mcp.prompt()
def configure_acl(site: str, policy: str = "deny") -> str:
    """Guide for configuring ACL traffic filtering rules for a Netris site."""
    return f"""
# ACL Configuration Guide: {site}

## Overview
Access Control Lists (ACLs) in Netris filter network traffic at the site level. They control which traffic is permitted or denied based on source/destination IP, protocol, and port. Netris applies ACLs on SoftGates and switches at {site}.

## Default Policy
The site's default ACL policy is currently "{policy}". This means traffic NOT matched by any rule is {policy}ed by default. To change the default policy, update the site configuration with `update_site`.

## Step 1: Review Existing ACLs
Use `list_acls` to see current ACL rules. Check for conflicts with what you want to add.
Use `get_acl` with a specific ACL ID to inspect an individual rule in detail.

## Step 2: Plan Your Rules
Netris processes ACL rules in order. Decide:
- What traffic to **permit**: internal east-west, management access, specific services
- What traffic to **deny**: inbound from untrusted sources, unused protocols

## Step 3: Create Permit Rules
For each traffic type to allow, use `create_acl` with:
- name: a descriptive name (e.g. "allow-ssh-from-mgmt")
- action: "permit"
- src_prefix: source CIDR (e.g. "10.10.0.0/24" for management network, "0.0.0.0/0" for any)
- dst_prefix: destination CIDR (e.g. "10.20.0.0/24" for server network, "0.0.0.0/0" for any)
- site: "{site}"
- protocol: "tcp", "udp", "icmp", or omit for all protocols
- dst_port: "22" for SSH, "80" for HTTP, "443" for HTTPS, "8080-8090" for a range

## Step 4: Create Deny Rules (if default policy is permit)
If the site default is "permit", explicitly deny unwanted traffic:
- Use `create_acl` with action: "deny"
- Order matters — deny rules should come after specific permit rules

## Step 5: Verify ACLs
Use `list_acls` to confirm all rules are in place and check the order.

## Common ACL Patterns
- **Allow SSH from management network**: action=permit, protocol=tcp, dst_port=22, src=mgmt_prefix
- **Allow HTTP/HTTPS from anywhere**: action=permit, protocol=tcp, dst_port=80 and dst_port=443, src=0.0.0.0/0
- **Block specific source**: action=deny, src_prefix=<untrusted>, dst_prefix=0.0.0.0/0
- **Allow ICMP for connectivity testing**: action=permit, protocol=icmp, src=0.0.0.0/0

## Removing Rules
Use `delete_acl` with the ACL ID to remove a rule. List rules with `list_acls` first to find the ID.

## Notes
- ACLs in Netris apply at the SoftGate/site boundary — they are not applied within a VNet
- For intra-VNet filtering, use dedicated firewall rules or security groups at the workload level
- Site configuration is viewable with `get_site` — use this to confirm the site's current default ACL policy
"""
