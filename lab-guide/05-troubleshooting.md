# 05 — Troubleshooting Guide

### 1. Controller Authentication Failure (HTTP 401)
- Verify `NETRIS_URL`, `NETRIS_USERNAME`, and `NETRIS_PASSWORD` in `.env`.
- Check if the password has special characters that need quoting.
- Test directly with `python setup_cli.py`.

### 2. Switch Execution Permission Denied
- Ensure you have SSH access to the controller jump host (`SSH_JUMP_HOST=adam-ctl.netris.io`).
- Switch show commands in FRR require elevated privileges: use `sudo vtysh -c 'show...'` rather than bare `vtysh`.

### 3. Missing Subnets / V-Nets
- By default, Netris scopes queries to the **Default VPC**. To view tenant resources across all VPCs, specify `vpc_name="all"` or pass explicit VPC filters.
