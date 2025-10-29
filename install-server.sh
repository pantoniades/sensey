#!/bin/bash
# Sensey Server Installation Script

set -e

INSTALL_DIR="/home/pi/sensey"
SERVICE_NAME="sensey-server"

echo "Installing Sensey Server as systemd service..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. Run as user 'pi'."
   exit 1
fi

# Create installation directory
echo "Creating installation directory..."
sudo mkdir -p $INSTALL_DIR
sudo chown pi:pi $INSTALL_DIR

# Copy server files
echo "Copying server files..."
cp -r sensey_server $INSTALL_DIR/
cp -r sensey_client $INSTALL_DIR/

# Set up configuration file
echo "Setting up configuration..."
cd $INSTALL_DIR/sensey_server
if [ ! -f sensey.ini ]; then
    if [ -f sensey.ini.example ]; then
        cp sensey.ini.example sensey.ini
        echo "Created sensey.ini from example (CSV storage by default)"
        echo "Edit sensey.ini to configure MySQL if needed"
    else
        echo "WARNING: sensey.ini.example not found!"
    fi
else
    echo "sensey.ini already exists, keeping existing configuration"
fi

# Set up Python virtual environment in server directory
echo "Setting up Python virtual environment..."
python3 -m venv . --system-site-packages
source bin/activate
pip install -r requirements.txt

# Create data directory for CSV storage
mkdir -p $INSTALL_DIR/sensey_server/data

# Copy and install systemd service
echo "Installing systemd service..."
sudo cp services/$SERVICE_NAME.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo "Installation complete!"
echo "To start the service: sudo systemctl start $SERVICE_NAME"
echo "To check status: sudo systemctl status $SERVICE_NAME"
echo "To view logs: sudo journalctl -u $SERVICE_NAME -f"