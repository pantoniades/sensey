#!/bin/bash
# Sensey Service Management Script
# Supports both systemd services and Podman containers

SERVICES=("sensey-server" "sensey-client-garden" "sensey-client-sensehat")
PODMAN_CONTAINERS=("sensey-server-csv" "sensey-server-mysql")

show_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|enable|disable} [service]"
    echo ""
    echo "Systemd Services:"
    echo "  server          - Sensey server (systemd)"
    echo "  garden          - Garden sensor client"
    echo "  sensehat        - Sense HAT client"
    echo ""
    echo "Podman Containers:"
    echo "  server-podman-csv    - Sensey server (Podman, CSV storage)"
    echo "  server-podman-mysql  - Sensey server (Podman, MySQL storage)"
    echo ""
    echo "Special:"
    echo "  all             - All systemd services"
    echo "  all-podman      - All Podman containers"
    echo ""
    echo "Examples:"
    echo "  $0 status all                    # Show status of all systemd services"
    echo "  $0 start server                  # Start systemd server service"
    echo "  $0 logs server-podman-csv        # Show Podman container logs"
    echo "  $0 restart server-podman-mysql   # Restart Podman container"
}

get_service_name() {
    case $1 in
        server)
            echo "sensey-server"
            ;;
        garden)
            echo "sensey-client-garden"
            ;;
        sensehat)
            echo "sensey-client-sensehat"
            ;;
        server-podman-csv)
            echo "sensey-server-csv"
            ;;
        server-podman-mysql)
            echo "sensey-server-mysql"
            ;;
        all)
            echo "all"
            ;;
        all-podman)
            echo "all-podman"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

is_podman_container() {
    local name=$1
    for container in "${PODMAN_CONTAINERS[@]}"; do
        if [[ "$container" == "$name" ]]; then
            return 0
        fi
    done
    return 1
}

execute_podman_command() {
    local cmd=$1
    local container=$2

    case $cmd in
        start)
            if podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
                podman start $container
            else
                echo "ERROR: Container $container does not exist. Deploy it first with install-server-podman.sh"
                return 1
            fi
            ;;
        stop)
            podman stop $container 2>/dev/null || echo "Container $container not running"
            ;;
        restart)
            podman restart $container
            ;;
        status)
            if podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
                echo "Container $container is running"
                podman ps --filter "name=$container" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            elif podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
                echo "Container $container exists but is not running"
                podman ps -a --filter "name=$container" --format "table {{.Names}}\t{{.Status}}"
            else
                echo "Container $container does not exist"
            fi
            ;;
        logs)
            podman logs -f $container
            ;;
        enable|disable)
            echo "ERROR: enable/disable not supported for Podman containers"
            echo "Containers are started with --restart unless-stopped by default"
            return 1
            ;;
        *)
            echo "ERROR: Unknown command: $cmd"
            return 1
            ;;
    esac
}

execute_command() {
    local cmd=$1
    local service=$2
    
    case $cmd in
        logs)
            sudo journalctl -u $service -f
            ;;
        *)
            sudo systemctl $cmd $service
            ;;
    esac
}

if [[ $# -lt 2 ]]; then
    show_usage
    exit 1
fi

COMMAND=$1
TARGET=$2

SERVICE_NAME=$(get_service_name $TARGET)

if [[ "$SERVICE_NAME" == "unknown" ]]; then
    echo "Error: Unknown service '$TARGET'"
    show_usage
    exit 1
fi

# Handle "all" - all systemd services
if [[ "$SERVICE_NAME" == "all" ]]; then
    for service in "${SERVICES[@]}"; do
        echo "=== $service ==="
        if systemctl is-active --quiet $service 2>/dev/null; then
            execute_command $COMMAND $service
        else
            echo "Service $service not installed or not active"
        fi
        echo ""
    done
    exit 0
fi

# Handle "all-podman" - all Podman containers
if [[ "$SERVICE_NAME" == "all-podman" ]]; then
    if ! command -v podman &> /dev/null; then
        echo "ERROR: Podman is not installed"
        exit 1
    fi
    for container in "${PODMAN_CONTAINERS[@]}"; do
        echo "=== $container ==="
        if podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
            execute_podman_command $COMMAND $container
        else
            echo "Container $container not deployed"
        fi
        echo ""
    done
    exit 0
fi

# Handle individual service/container
if is_podman_container "$SERVICE_NAME"; then
    # It's a Podman container
    if ! command -v podman &> /dev/null; then
        echo "ERROR: Podman is not installed"
        exit 1
    fi
    execute_podman_command $COMMAND $SERVICE_NAME
else
    # It's a systemd service
    execute_command $COMMAND $SERVICE_NAME
fi