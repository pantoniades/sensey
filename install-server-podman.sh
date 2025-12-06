#!/bin/bash
# Sensey Server - Podman Installation Script
# Containerized deployment for sensey-server using Podman

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$PROJECT_DIR/sensey_server"
IMAGE_NAME="localhost/sensey-server:latest"
DEPLOYMENT_TYPE=""

show_usage() {
    echo "Usage: $0 [--csv|--mysql]"
    echo ""
    echo "Deploy Sensey Server as a Podman container with:"
    echo "  --csv    CSV file-based storage (data stored in Podman volume)"
    echo "  --mysql  MySQL database storage (requires external MySQL 8.4+ server)"
    echo ""
    echo "Examples:"
    echo "  $0 --csv      # Deploy with CSV storage"
    echo "  $0 --mysql    # Deploy with MySQL storage"
}

echo "=== Sensey Server - Podman Installation ==="
echo ""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --csv)
            DEPLOYMENT_TYPE="csv"
            shift
            ;;
        --mysql)
            DEPLOYMENT_TYPE="mysql"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
done

if [[ -z "$DEPLOYMENT_TYPE" ]]; then
    echo "ERROR: Must specify deployment type"
    echo ""
    show_usage
    exit 1
fi

# Check if Podman is installed
echo "Checking prerequisites..."
if ! command -v podman &> /dev/null; then
    echo "ERROR: Podman is not installed."
    echo ""
    echo "Install Podman on Debian/Ubuntu:"
    echo "  sudo apt update"
    echo "  sudo apt install -y podman"
    echo ""
    echo "Install Podman on RHEL/Fedora:"
    echo "  sudo dnf install -y podman"
    exit 1
fi

echo "✓ Podman is installed: $(podman --version)"

# Check if server directory exists
if [ ! -d "$SERVER_DIR" ]; then
    echo "ERROR: Server directory not found: $SERVER_DIR"
    exit 1
fi

echo "✓ Server directory found"

# Build container image
echo ""
echo "Building container image..."
echo "This may take a few minutes on first run..."
cd "$SERVER_DIR"
podman build -t "$IMAGE_NAME" -f Containerfile .

if [ $? -eq 0 ]; then
    echo "✓ Container image built successfully: $IMAGE_NAME"
else
    echo "ERROR: Failed to build container image"
    exit 1
fi

# Deploy based on type
echo ""
echo "Deploying Sensey Server ($DEPLOYMENT_TYPE storage)..."

DEPLOY_DIR="$SERVER_DIR/podman/$DEPLOYMENT_TYPE"

if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deployment directory not found: $DEPLOY_DIR"
    exit 1
fi

# Run deployment script
cd "$DEPLOY_DIR"
./deploy.sh

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Deployment type: $DEPLOYMENT_TYPE"
echo "Container name:  sensey-server-$DEPLOYMENT_TYPE"
echo "Web interface:   http://localhost:5000"
echo ""
echo "Next steps:"
echo ""

if [ "$DEPLOYMENT_TYPE" = "mysql" ]; then
    echo "1. Configure MySQL connection:"
    echo "   Edit: $DEPLOY_DIR/sensey.ini"
    echo "   Update host, port, user, database"
    echo ""
    echo "2. Set MySQL password (choose one method):"
    echo ""
    echo "   a) Podman Secret (RECOMMENDED):"
    echo "      echo -n 'your_password' | podman secret create sensey_mysql_password -"
    echo "      podman restart sensey-server-mysql"
    echo ""
    echo "   b) Environment Variable:"
    echo "      podman stop sensey-server-mysql"
    echo "      podman rm sensey-server-mysql"
    echo "      export SENSEY_MYSQL_PASSWORD='your_password'"
    echo "      cd $DEPLOY_DIR && ./deploy.sh"
    echo ""
    echo "   c) Config File:"
    echo "      Edit $DEPLOY_DIR/sensey.ini and uncomment password line"
    echo "      podman restart sensey-server-mysql"
    echo ""
    echo "3. Ensure MySQL database and user exist:"
    echo "   CREATE DATABASE sensey;"
    echo "   CREATE USER 'sensey'@'%' IDENTIFIED BY 'your_password';"
    echo "   GRANT ALL PRIVILEGES ON sensey.* TO 'sensey'@'%';"
    echo ""
fi

echo "Management commands:"
echo "  podman ps                                    # View containers"
echo "  podman logs -f sensey-server-$DEPLOYMENT_TYPE  # View logs"
echo "  podman stop sensey-server-$DEPLOYMENT_TYPE     # Stop container"
echo "  podman start sensey-server-$DEPLOYMENT_TYPE    # Start container"
echo "  podman restart sensey-server-$DEPLOYMENT_TYPE  # Restart container"
echo ""
echo "Use manage-services.sh for unified management:"
echo "  $PROJECT_DIR/manage-services.sh status server-podman-$DEPLOYMENT_TYPE"
echo ""
