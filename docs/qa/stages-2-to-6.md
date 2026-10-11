# QA Report: Stages 2 through 6 (Full Pipeline Verification)

**Evaluator:** QA Gate Runner  
**Target Controller:** `https://adam-ctl.netris.io` (live controller v4.15.0-011)  
**Date:** 2026-10-11  
**Status:** **PASSED (Green)**

---

## 1. Test Execution & Coverage Matrix

| Test Suite | File | Tests Run | Result | Notes |
|---|---|---|---|---|
| **Stage 1 Foundation** | `tests/test_stage1_foundation.py` | 5 passed | **PASS** | Auth, 401 reauth, backoff retries, secret redaction |
| **Stage 2 Core Read Tools** | `tests/test_stage2_tools.py` | 4 passed | **PASS** | Live query of fabric inventory, V-Nets, eBGP sessions |
| **Stage 3 Diagnostics & Triage** | `tests/test_stage3_diagnostics.py` | 4 passed | **PASS** | Heartbeat alarms, Looking Glass peers, symptom triage |
| **Stage 4 & 5 Safety & Gating** | `tests/test_stage4_5_safety.py` | 2 passed | **PASS** | Command injection regex filters, read-only mutation block |
| **Static Code Quality** | `ruff check app/` | Clean | **PASS** | 0 lint errors |

**Total Regression:** 15/15 tests passing in 3.03s against the live Netris fabric.

---

## 2. Live Parity vs UI Survey

The UI survey completed by the browser agent confirmed:
- **Switches/Nodes:** 211 hardware entries queried live via `fabric_inventory(domain='hardware')`.
- **V-Nets:** 19 active overlay networks verified via `virtual_networks(action='list_vnets')`.
- **Border E-BGP:** 4 active sessions to AS 65401 verified via `routing_and_policy(action='ebgp_sessions')`.
- **Looking Glass:** 4 fabric peers responsive for live routing inspection.

---

## 3. Security & Safety Evaluation

1. **Credential Safety:**
   - Git status confirms `.env` is uncommitted and gitignored.
   - Credentials printed to stdout or logs are masked via `redact()`.
   - `conftest.py` does not override `.env` credentials with mock values.

2. **Command Injection Prevention:**
   - Switch execution helper rejects shell separators (`;`, `&&`, `||`, `|`, `>`, `<`, `` ` ``, `$`).
   - Only allow-listed show commands (`nv show`, `net show`, `vtysh -c 'show...'`, `ip route`) are accepted.

3. **Gated Mutations:**
   - Any mutation request in `read-only` mode returns an immediate HTTP/tool rejection without mutating controller state.
