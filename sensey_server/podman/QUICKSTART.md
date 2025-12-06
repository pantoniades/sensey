# Podman Deployment - Quick Start

## Install Podman

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y podman

# RHEL/Fedora
sudo dnf install -y podman
```

## Deploy Server

### CSV Storage

```bash
cd /path/to/sensey
./install-server-podman.sh --csv
```

Access: http://localhost:5000

### MySQL Storage

**1. Create MySQL database:**
```sql
CREATE DATABASE sensey;
CREATE USER 'sensey'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sensey.* TO 'sensey'@'%';
```

**2. Deploy container:**
```bash
cd /path/to/sensey
./install-server-podman.sh --mysql
```

**3. Configure MySQL connection:**
```bash
# Edit configuration
nano sensey_server/podman/mysql/sensey.ini
# Update: host, port, user, database

# Set password via Podman secret (recommended)
echo -n 'your_password' | podman secret create sensey_mysql_password -

# Restart container
podman restart sensey-server-mysql
```

Access: http://localhost:5000

## Common Commands

```bash
# View containers
podman ps

# View logs
podman logs -f sensey-server-csv
podman logs -f sensey-server-mysql

# Restart
podman restart sensey-server-csv
podman restart sensey-server-mysql

# Stop
podman stop sensey-server-csv
podman stop sensey-server-mysql

# Start
podman start sensey-server-csv
podman start sensey-server-mysql
```

## Using manage-services.sh

```bash
cd /path/to/sensey

# Status
./manage-services.sh status server-podman-csv
./manage-services.sh status server-podman-mysql

# Logs
./manage-services.sh logs server-podman-csv

# Restart
./manage-services.sh restart server-podman-mysql
```

## Backup Data (CSV only)

```bash
# Export volume
podman volume export sensey-data -o backup.tar

# Import volume
podman volume import sensey-data backup.tar
```

## Update Application

```bash
cd /path/to/sensey

# Pull latest code
git pull

# Rebuild image
cd sensey_server
podman build -t localhost/sensey-server:latest -f Containerfile .

# Restart (CSV example)
podman stop sensey-server-csv
podman rm sensey-server-csv
cd podman/csv
./deploy.sh
```

## Troubleshooting

**Check health:**
```bash
curl http://localhost:5000/health
```

**View detailed logs:**
```bash
podman logs sensey-server-csv
```

**Check configuration:**
```bash
# CSV
cat sensey_server/podman/csv/sensey.ini

# MySQL
cat sensey_server/podman/mysql/sensey.ini
```

**Verify MySQL password:**
```bash
# List secrets
podman secret ls

# Test connection
podman exec -it sensey-server-mysql python -c "import config; print(config.get_config().get_storage_config())"
```

## Full Documentation

See [README.md](README.md) for complete documentation.
