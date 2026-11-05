#!/usr/bin/env bash
set -euo pipefail
# Create a dedicated virtual environment for Antigravity
VENV_DIR="$HOME/.antigravity_venv"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
# Upgrade pip and install Antigravity CLI
pip install --upgrade pip
pip install antigravity-cli
# Verify installation
antigravity-cli --version
# Create user-level systemd service unit for Antigravity MCP server
SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"
cat > "$SYSTEMD_DIR/antigravity.service" <<'EOF'
[Unit]
Description=Antigravity MCP Server
After=network.target

[Service]
Type=simple
ExecStart=$HOME/.antigravity_venv/bin/antigravity-cli mcp
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
# Reload systemd daemon for user units and enable/start service
systemctl --user daemon-reload
systemctl --user enable antigravity.service
systemctl --user start antigravity.service
echo "Antigravity installation complete and service started."
