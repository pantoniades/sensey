#!/bin/bash
# Sensey Server - CSV Deployment Script (Podman)
# Deploys sensey-server container with CSV file-based storage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_NAME="localhost/sensey-server:latest"
CONTAINER_NAME="sensey-server-csv"

echo "=== Sensey Server - CSV Deployment (Podman) ==="
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
    echo "  ./install-server-podman.sh --csv"
    exit 1
fi

# Check if sensey.ini exists
if [ ! -f "$SCRIPT_DIR/sensey.ini" ]; then
    echo "ERROR: Configuration file not found: $SCRIPT_DIR/sensey.ini"
    echo "The CSV deployment uses sensey.ini from this directory."
    echo "It should already exist. If missing, something went wrong during installation."
    exit 1
fi

# Stop and remove existing container if running
if podman ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    podman stop "$CONTAINER_NAME" 2>/dev/null || true
    podman rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Create named volume if it doesn't exist
if ! podman volume exists sensey-data; then
    echo "Creating data volume..."
    podman volume create sensey-data
fi

echo "Deploying Sensey Server with CSV storage..."
podman run -d \
    --name "$CONTAINER_NAME" \
    -p 5000:5000 \
    -v "$SCRIPT_DIR/sensey.ini:/app/sensey.ini:ro,Z" \
    -v sensey-data:/app/data:Z \
    --restart unless-stopped \
    "$IMAGE_NAME"

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
echo "Data volume: sensey-data"
echo "  podman volume inspect sensey-data  # View volume details"
echo ""
