#!/bin/bash
# Sensey Client Installation Script

set -e

INSTALL_DIR="/home/pi/sensey"
CLIENT_TYPE=""

echo "Installing Sensey Client as systemd service..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. Run as user 'pi'."
   exit 1
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --garden)
      CLIENT_TYPE="garden"
      shift
      ;;
    --sensehat)
      CLIENT_TYPE="sensehat"
      shift
      ;;
    *)
      echo "Usage: $0 [--garden|--sensehat]"
      echo "  --garden   Install garden sensor client"
      echo "  --sensehat Install Sense HAT client"
      exit 1
      ;;
  esac
done

if [[ -z "$CLIENT_TYPE" ]]; then
  echo "Error: Must specify client type"
  echo "Usage: $0 [--garden|--sensehat]"
  exit 1
fi

SERVICE_NAME="sensey-client-$CLIENT_TYPE"

# Create installation directory
echo "Creating installation directory..."
sudo mkdir -p $INSTALL_DIR
sudo chown pi:pi $INSTALL_DIR

# Copy client files
echo "Copying client files..."
cp -r sensey_client $INSTALL_DIR/

# Install Python dependencies
echo "Installing Python dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-setuptools

# Install sensor-specific dependencies
if [[ "$CLIENT_TYPE" == "garden" ]]; then
  echo "Installing garden sensor dependencies..."
  sudo apt install -y python3-smbus python3-spidev
  pip3 install --user adafruit-circuitpython-htu21d adafruit-circuitpython-bh1750
elif [[ "$CLIENT_TYPE" == "sensehat" ]]; then
  echo "Installing Sense HAT dependencies..."
  sudo apt install -y sense-hat
  pip3 install --user sense-hat
fi

# Install common dependencies
pip3 install --user requests configparser

# Copy and install systemd service
echo "Installing systemd service..."
sudo cp services/$SERVICE_NAME.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo "Installation complete!"
echo "Configure server connection in $INSTALL_DIR/sensey_client/sensey.ini"
echo "To start the service: sudo systemctl start $SERVICE_NAME"
echo "To check status: sudo systemctl status $SERVICE_NAME"
echo "To view logs: sudo journalctl -u $SERVICE_NAME -f"