# Sensey Server - Podman Deployment

This directory contains configurations and scripts for deploying Sensey Server as a containerized application using Podman.

## Overview

The Podman deployment provides:
- **Portable deployment** - Run anywhere Podman is available
- **Isolated environment** - No conflicts with system Python packages
- **Easy updates** - Rebuild image and restart container
- **Two storage options** - CSV file-based or MySQL database
- **Secrets management** - Secure password handling via Podman secrets

## Quick Start

### Prerequisites

- Podman installed (tested with Podman 3.0+)
- For MySQL: External MySQL 8.4+ server with database and user created

**Install Podman:**
```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y podman

# RHEL/Fedora/CentOS
sudo dnf install -y podman
```

### Installation

From the project root directory:

**CSV Storage (recommended for simple deployments):**
```bash
./install-server-podman.sh --csv
```

**MySQL Storage (recommended for production):**
```bash
./install-server-podman.sh --mysql
```

The installer will:
1. Build the container image
2. Create deployment configuration
3. Deploy and start the container
4. Display management instructions

### Access

After deployment, access the web interface at:
- **Local:** http://localhost:5000
- **Network:** http://YOUR_IP:5000

Clients connect to: `http://YOUR_IP:5000/data/<client_id>`

## Directory Structure

```
podman/
├── README.md              # This file
├── csv/                   # CSV storage deployment
│   ├── sensey.ini         # Configuration file
│   ├── compose.yaml       # Podman Compose file
│   └── deploy.sh          # Deployment script
├── mysql/                 # MySQL storage deployment
│   ├── sensey.ini         # Configuration file
│   ├── compose.yaml       # Podman Compose file
│   └── deploy.sh          # Deployment script
└── systemd/               # Systemd integration (optional)
    └── sensey-server-podman.service
```

## Storage Options

### CSV Storage

**Best for:**
- Development and testing
- Single-host deployments
- Simple setup with no external dependencies

**Features:**
- Data stored in Podman volume `sensey-data`
- Survives container restarts and recreation
- Easy backup with `podman volume export`

**Container name:** `sensey-server-csv`

**Data volume:** `sensey-data`

### MySQL Storage

**Best for:**
- Production environments
- Multiple server instances (load balancing)
- Advanced querying and reporting
- Integration with existing MySQL infrastructure

**Features:**
- Connects to external MySQL 8.4+ server
- Supports connection pooling
- Secure password management via Podman secrets

**Container name:** `sensey-server-mysql`

**Required MySQL setup:**
```sql
CREATE DATABASE sensey;
CREATE USER 'sensey'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sensey.* TO 'sensey'@'%';
FLUSH PRIVILEGES;
```

## Configuration

### CSV Configuration

Edit `csv/sensey.ini`:
```ini
[storage]
backend = csv

[csv]
data_dir = data  # Don't change - mounted volume
```

### MySQL Configuration

Edit `mysql/sensey.ini`:
```ini
[storage]
backend = mysql

[mysql]
host = mysql.example.com
port = 3306
user = sensey
database = sensey
pool_size = 5
# password managed via Podman secret (see below)
```

## Secrets Management (MySQL Only)

Three methods to provide MySQL password, in priority order:

### 1. Podman Secret (RECOMMENDED)

Most secure method - password never appears in config files or environment.

```bash
# Create secret
echo 'your_mysql_password' | podman secret create sensey_mysql_password -

# Deploy/restart container
cd sensey_server/podman/mysql
./deploy.sh
```

**Update secret:**
```bash
# Remove old secret
podman secret rm sensey_mysql_password

# Create new secret
echo 'new_password' | podman secret create sensey_mysql_password -

# Restart container
podman restart sensey-server-mysql
```

### 2. Environment Variable

Useful for CI/CD pipelines or temporary deployments.

```bash
export SENSEY_MYSQL_PASSWORD='your_password'
cd sensey_server/podman/mysql
./deploy.sh
```

**Note:** Password must be exported each time before running `deploy.sh`

### 3. Config File

Least secure - password stored in plain text.

Edit `mysql/sensey.ini`:
```ini
[mysql]
password = your_password_here
```

Then restart:
```bash
podman restart sensey-server-mysql
```

## Management Commands

### Using Podman Directly

```bash
# View running containers
podman ps

# View all containers (including stopped)
podman ps -a

# View logs
podman logs sensey-server-csv
podman logs -f sensey-server-mysql  # Follow logs

# Start/stop/restart
podman start sensey-server-csv
podman stop sensey-server-csv
podman restart sensey-server-csv

# View resource usage
podman stats sensey-server-csv

# Execute command in container
podman exec -it sensey-server-csv python --version

# Remove container
podman stop sensey-server-csv
podman rm sensey-server-csv
```

### Using manage-services.sh

Unified management for all Sensey services (from project root):

```bash
# Status
./manage-services.sh status server-podman-csv
./manage-services.sh status server-podman-mysql
./manage-services.sh status all-podman

# Start/stop/restart
./manage-services.sh start server-podman-csv
./manage-services.sh stop server-podman-mysql
./manage-services.sh restart server-podman-csv

# Logs
./manage-services.sh logs server-podman-mysql
```

## Volume Management (CSV Storage)

### Inspect Volume

```bash
podman volume inspect sensey-data
```

### Backup Data

```bash
# Export volume to tar archive
podman volume export sensey-data -o sensey-data-backup.tar

# Or copy from mounted location
podman run --rm -v sensey-data:/data:ro -v $(pwd):/backup alpine \
    tar czf /backup/sensey-data-backup.tar.gz -C /data .
```

### Restore Data

```bash
# Import from tar archive
podman volume import sensey-data sensey-data-backup.tar

# Or copy to mounted location
podman run --rm -v sensey-data:/data -v $(pwd):/backup alpine \
    tar xzf /backup/sensey-data-backup.tar.gz -C /data
```

### Delete Volume

**⚠️ WARNING: This permanently deletes all data!**

```bash
# Stop and remove container first
podman stop sensey-server-csv
podman rm sensey-server-csv

# Delete volume
podman volume rm sensey-data
```

## Updating the Application

### Update to Latest Code

```bash
# 1. Navigate to project root
cd /path/to/sensey

# 2. Pull latest code
git pull

# 3. Rebuild image
cd sensey_server
podman build -t localhost/sensey-server:latest -f Containerfile .

# 4. Restart container (CSV example)
podman stop sensey-server-csv
podman rm sensey-server-csv
cd podman/csv
./deploy.sh
```

**Note:** Data volumes (CSV) are preserved during updates.

## Troubleshooting

### Container won't start

Check logs:
```bash
podman logs sensey-server-csv
```

Common issues:
- Port 5000 already in use: Change port in `deploy.sh` or `compose.yaml`
- Config file missing: Ensure `sensey.ini` exists in deployment directory
- MySQL connection failed: Verify host, port, user, database, and password

### Health check failing

Test health endpoint manually:
```bash
curl http://localhost:5000/health
```

Should return:
```json
{"status": "healthy", "storage": "accessible"}
```

### Permission denied errors

SELinux contexts may be incorrect. Redeploy with correct `:Z` flag:
```bash
podman stop sensey-server-csv
podman rm sensey-server-csv
cd sensey_server/podman/csv
./deploy.sh
```

### Container exists but can't be removed

Force remove:
```bash
podman rm -f sensey-server-csv
```

## Advanced Configuration

### Resource Limits

Edit `compose.yaml` and uncomment:
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
```

Then redeploy:
```bash
podman-compose down
podman-compose up -d
```

Or with podman run:
```bash
podman run -d \
    --name sensey-server-csv \
    --memory=512m \
    --cpus=1.0 \
    # ... other options ...
    localhost/sensey-server:latest
```

### Custom Port

Change port mapping in `deploy.sh` or `compose.yaml`:
```bash
# Deploy on port 8080 instead of 5000
-p 8080:5000
```

### Network Configuration

Create custom network for multiple containers:
```bash
# Create network
podman network create sensey-net

# Run container on network
podman run -d \
    --name sensey-server-csv \
    --network sensey-net \
    # ... other options ...
    localhost/sensey-server:latest
```

## Systemd Integration

For automatic start on boot:

```bash
# Copy service file
sudo cp systemd/sensey-server-podman.service /etc/systemd/system/

# Edit service file to match your deployment (csv or mysql)
sudo nano /etc/systemd/system/sensey-server-podman.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable sensey-server-podman.service
sudo systemctl start sensey-server-podman.service
```

**Note:** Ensure container is created before enabling systemd service.

## Comparison: Podman vs Systemd Deployment

| Feature | Podman | Systemd (Native) |
|---------|--------|------------------|
| Isolation | Full container isolation | Process isolation only |
| Dependencies | Bundled in image | System packages required |
| Updates | Rebuild image | pip install |
| Portability | Run anywhere | Tied to host system |
| Resource limits | Easy (--memory, --cpus) | Requires cgroups config |
| Setup complexity | Medium | Low |
| Performance | Slight overhead | Native |
| Best for | Production, multiple hosts | Development, simple deployments |

## Support

For issues, questions, or contributions:
- **Project:** https://github.com/yourusername/sensey
- **Issues:** https://github.com/yourusername/sensey/issues
- **Documentation:** See main README.md
