#!/bin/bash
# Sensey Server - MySQL Deployment Script (Podman)
# Deploys sensey-server container with external MySQL database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_NAME="localhost/sensey-server:latest"
CONTAINER_NAME="sensey-server-mysql"
SECRET_NAME="sensey_mysql_password"

echo "=== Sensey Server - MySQL Deployment (Podman) ==="
echo ""

# Check if Podman is installed
if ! command -v podman &> /dev/null; then
    echo "ERROR: Podman is not installed."
    echo "Install with: sudo apt install podman"
    exit 1
fi

# Check if image exists
if ! podman image exists "$IMAGE_NAME"; then
    echo "ERROR: Container image not found: $IMAGE_NAME"
    echo ""
    echo "Build the image first:"
    echo "  cd $SERVER_DIR"
    echo "  podman build -t $IMAGE_NAME -f Containerfile ."
    echo ""
    echo "Or run the project installer:"
    echo "  cd $(dirname $(dirname $SERVER_DIR))"
    echo "  ./install-server-podman.sh --mysql"
    exit 1
fi

# Check if sensey.ini exists
if [ ! -f "$SCRIPT_DIR/sensey.ini" ]; then
    echo "ERROR: Configuration file not found: $SCRIPT_DIR/sensey.ini"
    echo "The MySQL deployment uses sensey.ini from this directory."
    echo "Update it with your MySQL connection details before deploying."
    exit 1
fi

# Check for MySQL password (secret, env var, or config file)
USE_SECRET=false
if podman secret exists "$SECRET_NAME" 2>/dev/null; then
    echo "Found Podman secret: $SECRET_NAME"
    USE_SECRET=true
elif [ -n "$SENSEY_MYSQL_PASSWORD" ]; then
    echo "Using password from SENSEY_MYSQL_PASSWORD environment variable"
elif grep -q "^password\s*=" "$SCRIPT_DIR/sensey.ini"; then
    echo "Using password from sensey.ini configuration file"
else
    echo ""
    echo "WARNING: No MySQL password configured!"
    echo ""
    echo "Choose one of the following methods to provide the password:"
    echo ""
    echo "1. Podman Secret (RECOMMENDED - most secure):"
    echo "   echo 'your_password' | podman secret create $SECRET_NAME -"
    echo "   Then run this script again."
    echo ""
    echo "2. Environment Variable:"
    echo "   export SENSEY_MYSQL_PASSWORD='your_password'"
    echo "   Then run this script again."
    echo ""
    echo "3. Config File (least secure):"
    echo "   Edit $SCRIPT_DIR/sensey.ini"
    echo "   Uncomment and set: password = your_password"
    echo ""
    read -p "Continue without password? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stop and remove existing container if running
if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    podman stop "$CONTAINER_NAME" 2>/dev/null || true
    podman rm "$CONTAINER_NAME" 2>/dev/null || true
fi

echo "Deploying Sensey Server with MySQL storage..."

# Build podman run command
CMD="podman run -d \
    --name $CONTAINER_NAME \
    -p 5000:5000 \
    -v $SCRIPT_DIR/sensey.ini:/app/sensey.ini:ro,Z \
    --restart unless-stopped"

# Add secret if available
if [ "$USE_SECRET" = true ]; then
    CMD="$CMD --secret $SECRET_NAME,type=env,target=SENSEY_MYSQL_PASSWORD"
fi

# Add environment variable if set
if [ -n "$SENSEY_MYSQL_PASSWORD" ]; then
    CMD="$CMD -e SENSEY_MYSQL_PASSWORD"
fi

# Add image name
CMD="$CMD $IMAGE_NAME"

# Execute deployment
eval $CMD

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Container: $CONTAINER_NAME"
echo "Status:    $(podman ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}")"
echo "Web UI:    http://localhost:5000"
echo ""
echo "Management commands:"
echo "  podman ps                          # View running containers"
echo "  podman logs -f $CONTAINER_NAME     # View logs"
echo "  podman stop $CONTAINER_NAME        # Stop container"
echo "  podman start $CONTAINER_NAME       # Start container"
echo "  podman restart $CONTAINER_NAME     # Restart container"
echo ""
echo "MySQL Configuration:"
echo "  Edit $SCRIPT_DIR/sensey.ini to update connection settings"
echo ""
if [ "$USE_SECRET" = true ]; then
    echo "Password: Using Podman secret '$SECRET_NAME'"
    echo "  Update: echo 'new_password' | podman secret create ${SECRET_NAME}_new -"
elif [ -n "$SENSEY_MYSQL_PASSWORD" ]; then
    echo "Password: Using environment variable SENSEY_MYSQL_PASSWORD"
else
    echo "Password: Using password from sensey.ini (or none)"
fi
echo ""
