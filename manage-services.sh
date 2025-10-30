#!/bin/bash
# Sensey Service Management Script

SERVICES=("sensey-server" "sensey-client-garden" "sensey-client-sensehat")

show_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|enable|disable} [service]"
    echo ""
    echo "Services: server, garden, sensehat, all"
    echo ""
    echo "Examples:"
    echo "  $0 status all          # Show status of all services"
    echo "  $0 start server        # Start server service"
    echo "  $0 logs garden         # Show garden client logs"
    echo "  $0 restart sensehat    # Restart sensehat client"
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
        all)
            echo "all"
            ;;
        *)
            echo "unknown"
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
else
    execute_command $COMMAND $SERVICE_NAME
fi