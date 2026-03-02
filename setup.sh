#!/bin/bash

# =============================================================================
# Traffic Light Simulator - LXC Setup Script
# This runs INSIDE the LXC container after creation
# =============================================================================

set -e

echo "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

echo "Installing dependencies..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl

echo "Cloning Traffic Light Simulator repository..."
cd /opt
git clone https://github.com/DawsonFinnie/Traffic-Lights.git traffic-light
cd traffic-light

echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing Python packages..."
pip install --quiet -r requirements.txt

echo "Creating systemd service..."
cat > /etc/systemd/system/traffic-light.service << EOF
[Unit]
Description=Traffic Light Simulator
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/traffic-light
ExecStart=/opt/traffic-light/venv/bin/python -m app.main
Restart=always
RestartSec=5
EnvironmentFile=/etc/environment

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable traffic-light
systemctl start traffic-light

echo "Setup complete!"
systemctl status traffic-light --no-pager
