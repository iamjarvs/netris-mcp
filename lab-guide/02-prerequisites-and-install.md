# 02 — Prerequisites & Installation

## Prerequisites
- macOS or Linux
- Python 3.10+ (tested through Python 3.14)
- Target Netris Controller credentials (e.g., `https://adam-ctl.netris.io`)

## Fast Install & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamjarvs/netris-mcp.git
   cd netris-mcp
   ```

2. **Run the interactive setup wizard:**
   ```bash
   python3 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ./.venv/bin/python setup_cli.py
   ```
   The wizard validates authentication against your Netris Controller and automatically generates:
   - `.env` configuration file
   - `.vscode/mcp.json` IDE integration file
   - `claude_desktop_config.example.json`
