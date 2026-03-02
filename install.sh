#!/bin/bash

# =============================================================================
# Traffic Light Simulator - Proxmox LXC Installer
# Run this script from the Proxmox host shell
# =============================================================================

set -e

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Check we are running on Proxmox ---
if ! command -v pct &> /dev/null; then
    echo -e "${RED}Error: This script must be run on a Proxmox host.${NC}"
    exit 1
fi

# --- Welcome screen ---
whiptail --title "Traffic Light Simulator" \
    --msgbox "Welcome to the Traffic Light Simulator LXC Installer.\n\nThis will create a new LXC container and install the Traffic Light Simulator with BACnet support.\n\nPress OK to continue." \
    14 60

# --- Collect settings with defaults pre-filled ---
CT_ID=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter CT ID:" 8 40 "103" 3>&1 1>&2 2>&3)

HOSTNAME=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter hostname:" 8 40 "traffic-light" 3>&1 1>&2 2>&3)

IP=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter IP address (CIDR format):" 8 40 "192.168.30.12/24" 3>&1 1>&2 2>&3)

GATEWAY=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter gateway:" 8 40 "192.168.30.1" 3>&1 1>&2 2>&3)

VLAN=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter VLAN tag (leave blank for none):" 8 40 "30" 3>&1 1>&2 2>&3)

STORAGE=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter Proxmox storage:" 8 40 "local-lvm" 3>&1 1>&2 2>&3)

BRIDGE=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter network bridge:" 8 40 "vmbr0" 3>&1 1>&2 2>&3)

BACNET_DEVICE_ID=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter BACnet Device ID:" 8 40 "3001" 3>&1 1>&2 2>&3)

WEB_PORT=$(whiptail --title "Traffic Light Simulator" \
    --inputbox "Enter web UI port:" 8 40 "8500" 3>&1 1>&2 2>&3)

# --- Confirm settings ---
whiptail --title "Traffic Light Simulator - Confirm Settings" \
    --yesno "Please confirm the following settings:\n\n  CT ID:          $CT_ID\n  Hostname:       $HOSTNAME\n  IP Address:     $IP\n  Gateway:        $GATEWAY\n  VLAN:           $VLAN\n  Storage:        $STORAGE\n  Bridge:         $BRIDGE\n  BACnet ID:      $BACNET_DEVICE_ID\n  Web Port:       $WEB_PORT\n\nProceed with installation?" \
    18 60

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installation cancelled.${NC}"
    exit 0
fi

echo -e "${GREEN}Starting installation...${NC}"

# --- Download the Ubuntu 22.04 template if not already present ---
echo -e "${YELLOW}Checking for Ubuntu 22.04 template...${NC}"
if ! pveam list local | grep -q "ubuntu-22.04"; then
    echo -e "${YELLOW}Downloading Ubuntu 22.04 template...${NC}"
    pveam update
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
fi

TEMPLATE=$(pveam list local | grep "ubuntu-22.04" | awk '{print $1}' | head -1)

# --- Build network config string ---
NET_CONFIG="name=eth0,bridge=${BRIDGE},ip=${IP},gw=${GATEWAY}"
if [ -n "$VLAN" ]; then
    NET_CONFIG="${NET_CONFIG},tag=${VLAN}"
fi

# --- Create the LXC ---
echo -e "${YELLOW}Creating LXC container ${CT_ID}...${NC}"
pct create $CT_ID $TEMPLATE \
    --hostname $HOSTNAME \
    --storage $STORAGE \
    --rootfs ${STORAGE}:4 \
    --memory 512 \
    --cores 1 \
    --net0 $NET_CONFIG \
    --unprivileged 1 \
    --features nesting=1 \
    --start 1 \
    --onboot 1

echo -e "${YELLOW}Waiting for container to start...${NC}"
sleep 5

# --- Push environment variables into the container ---
pct exec $CT_ID -- bash -c "echo 'BACNET_DEVICE_ID=${BACNET_DEVICE_ID}' >> /etc/environment"
pct exec $CT_ID -- bash -c "echo 'BACNET_IP=${IP}' >> /etc/environment"
pct exec $CT_ID -- bash -c "echo 'WEB_PORT=${WEB_PORT}' >> /etc/environment"

# --- Run the setup script inside the container ---
echo -e "${YELLOW}Running setup inside container...${NC}"
pct exec $CT_ID -- bash -c "$(wget -qLO - https://raw.githubusercontent.com/DawsonFinnie/Traffic-Lights/main/setup.sh)"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "  Web UI:    http://${IP%/*}:${WEB_PORT}"
echo -e "  BACnet:    Device ID ${BACNET_DEVICE_ID} on ${IP%/*}"
echo -e "  Manage:    pct enter ${CT_ID}"
echo -e "${GREEN}============================================${NC}"
