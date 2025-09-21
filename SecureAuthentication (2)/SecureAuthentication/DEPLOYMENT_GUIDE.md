# Deployment Guide - Secure Authentication System

## Overview

This guide provides step-by-step instructions for deploying the Secure Authentication System in various environments, from development to production.

## Table of Contents

- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security Configuration](#security-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Backup & Recovery](#backup--recovery)
- [Performance Optimization](#performance-optimization)

## Development Deployment

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- Git
- Virtual environment (recommended)

### Step 1: Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd SecureAuthentication

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup

```bash
# Start MySQL service
# Windows
net start mysql
# Linux
sudo systemctl start mysql
# Mac
brew services start mysql

# Create database
mysql -u root -p
```

```sql
CREATE DATABASE secure;
USE secure;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    image_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Step 3: Configuration

Create `.env` file:

```bash
# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=secure

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-development-secret-key
DEBUG=True

# Face Recognition
DEEPFACE_MODEL=VGG-Face
DEEPFACE_BACKEND=opencv
```

### Step 4: Run Application

```bash
python app.py
```

Application will be available at `http://127.0.0.1:5000`

## Production Deployment

### Prerequisites

- Ubuntu 20.04+ (recommended)
- Python 3.8+
- MySQL 8.0+
- Nginx
- SSL Certificate
- Domain name

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install MySQL
sudo apt install mysql-server -y

# Install Nginx
sudo apt install nginx -y

# Install SSL tools
sudo apt install certbot python3-certbot-nginx -y
```

### Step 2: Application Deployment

```bash
# Create application user
sudo useradd -m -s /bin/bash authapp
sudo usermod -aG sudo authapp

# Switch to application user
sudo su - authapp

# Clone repository
git clone <repository-url> /home/authapp/secure-auth
cd /home/authapp/secure-auth

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

### Step 3: Database Configuration

```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
```

```sql
CREATE DATABASE secure;
CREATE USER 'auth_user'@'localhost' IDENTIFIED BY 'secure_password_here';
GRANT ALL PRIVILEGES ON secure.* TO 'auth_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 4: Application Configuration

Create production configuration file:

```bash
# Create config file
nano /home/authapp/secure-auth/config.py
```

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-super-secret-production-key'
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_USER = os.environ.get('DB_USER') or 'auth_user'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'secure_password_here'
    DB_NAME = os.environ.get('DB_NAME') or 'secure'
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Face recognition settings
    DEEPFACE_MODEL = 'VGG-Face'
    DEEPFACE_BACKEND = 'opencv'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = '/home/authapp/secure-auth/faces'
```

### Step 5: Gunicorn Configuration

Create Gunicorn configuration:

```bash
nano /home/authapp/secure-auth/gunicorn.conf.py
```

```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Step 6: Systemd Service

Create systemd service file:

```bash
sudo nano /etc/systemd/system/secure-auth.service
```

```ini
[Unit]
Description=Secure Authentication System
After=network.target mysql.service

[Service]
User=authapp
Group=authapp
WorkingDirectory=/home/authapp/secure-auth
Environment="PATH=/home/authapp/secure-auth/venv/bin"
ExecStart=/home/authapp/secure-auth/venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable secure-auth
sudo systemctl start secure-auth
sudo systemctl status secure-auth
```

### Step 7: Nginx Configuration

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/secure-auth
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Proxy to Flask application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Serve face images directly
    location /faces/ {
        alias /home/authapp/secure-auth/faces/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Serve static files
    location /static/ {
        alias /home/authapp/secure-auth/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security: Block access to sensitive files
    location ~ /\. {
        deny all;
    }
    
    location ~ \.(py|pyc|pyo|log)$ {
        deny all;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/secure-auth /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 8: SSL Certificate

```bash
# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p faces static/faces

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=db
      - DB_USER=auth_user
      - DB_PASSWORD=secure_password
      - DB_NAME=secure
      - SECRET_KEY=your-secret-key
    volumes:
      - ./faces:/app/faces
      - ./static:/app/static
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=secure
      - MYSQL_USER=auth_user
      - MYSQL_PASSWORD=secure_password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
    restart: unless-stopped

volumes:
  mysql_data:
```

### Deployment Commands

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Update application
docker-compose pull
docker-compose up -d
```

## Cloud Deployment

### AWS Deployment

#### EC2 Instance Setup

```bash
# Launch EC2 instance (Ubuntu 20.04)
# Install Docker
sudo apt update
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker ubuntu

# Clone and deploy
git clone <repository-url>
cd SecureAuthentication
docker-compose up -d
```

#### RDS Database Setup

```bash
# Create RDS MySQL instance
# Update database configuration in docker-compose.yml
# Use RDS endpoint as DB_HOST
```

#### Load Balancer Configuration

```bash
# Create Application Load Balancer
# Configure health checks
# Set up SSL certificate in ACM
```

### Google Cloud Platform

#### App Engine Deployment

Create `app.yaml`:

```yaml
runtime: python39

env_variables:
  DB_HOST: your-cloud-sql-ip
  DB_USER: auth_user
  DB_PASSWORD: secure_password
  DB_NAME: secure
  SECRET_KEY: your-secret-key

automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6

handlers:
- url: /.*
  script: auto
```

Deploy:

```bash
gcloud app deploy
```

### Azure Deployment

#### Container Instances

```bash
# Create resource group
az group create --name secure-auth-rg --location eastus

# Create container instance
az container create \
  --resource-group secure-auth-rg \
  --name secure-auth \
  --image your-registry/secure-auth:latest \
  --ports 5000 \
  --environment-variables \
    DB_HOST=your-database-server \
    DB_USER=auth_user \
    DB_PASSWORD=secure_password \
    DB_NAME=secure \
    SECRET_KEY=your-secret-key
```

## Security Configuration

### Environment Variables

```bash
# Production environment variables
export FLASK_ENV=production
export SECRET_KEY=$(openssl rand -hex 32)
export DB_HOST=your-database-host
export DB_USER=auth_user
export DB_PASSWORD=$(openssl rand -base64 32)
export DB_NAME=secure
```

### Firewall Configuration

```bash
# UFW firewall setup
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5000/tcp  # Block direct access to Flask
```

### Database Security

```sql
-- Create restricted database user
CREATE USER 'auth_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT SELECT, INSERT, UPDATE ON secure.users TO 'auth_user'@'localhost';
FLUSH PRIVILEGES;

-- Remove root remote access
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
FLUSH PRIVILEGES;
```

### File Permissions

```bash
# Set proper file permissions
sudo chown -R authapp:authapp /home/authapp/secure-auth
sudo chmod -R 755 /home/authapp/secure-auth
sudo chmod 600 /home/authapp/secure-auth/.env
```

## Monitoring & Logging

### Application Logging

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/secure-auth.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Secure Auth startup')
```

### System Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs -y

# Monitor application
sudo systemctl status secure-auth
sudo journalctl -u secure-auth -f

# Monitor resources
htop
df -h
free -h
```

### Log Rotation

```bash
# Configure logrotate
sudo nano /etc/logrotate.d/secure-auth
```

```
/home/authapp/secure-auth/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 authapp authapp
    postrotate
        systemctl reload secure-auth
    endscript
}
```

## Backup & Recovery

### Database Backup

```bash
# Create backup script
nano /home/authapp/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/authapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/secure_auth_$DATE.sql"

mkdir -p $BACKUP_DIR

mysqldump -u auth_user -p'secure_password' secure > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

```bash
# Make executable and schedule
chmod +x /home/authapp/backup_db.sh
crontab -e
```

Add to crontab:
```
0 2 * * * /home/authapp/backup_db.sh
```

### Application Backup

```bash
# Backup application files
tar -czf /home/authapp/backups/app_$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /home/authapp/secure-auth/
```

### Recovery Process

```bash
# Restore database
gunzip -c /home/authapp/backups/secure_auth_20240101_020000.sql.gz | \
  mysql -u auth_user -p'secure_password' secure

# Restore application
tar -xzf /home/authapp/backups/app_20240101.tar.gz -C /home/authapp/
```

## Performance Optimization

### Database Optimization

```sql
-- Add indexes
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_created_at ON users(created_at);

-- Optimize table
OPTIMIZE TABLE users;
```

### Application Optimization

```python
# Connection pooling
from mysql.connector import pooling

db_pool = pooling.MySQLConnectionPool(
    pool_name="auth_pool",
    pool_size=10,
    pool_reset_session=True,
    **db_config
)

def get_db_connection():
    return db_pool.get_connection()
```

### Caching

```python
# Redis caching
import redis
from flask_caching import Cache

redis_client = redis.Redis(host='localhost', port=6379, db=0)
cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': 'redis://localhost:6379/0'})

@cache.memoize(timeout=300)
def get_user_data(username):
    # Expensive database operation
    pass
```

### CDN Configuration

```bash
# CloudFlare setup
# 1. Add domain to CloudFlare
# 2. Configure DNS
# 3. Enable caching for static assets
# 4. Configure SSL/TLS
```

## Troubleshooting

### Common Issues

#### Application Won't Start

```bash
# Check logs
sudo journalctl -u secure-auth -f

# Check port availability
sudo netstat -tlnp | grep :5000

# Check permissions
ls -la /home/authapp/secure-auth/
```

#### Database Connection Issues

```bash
# Test database connection
mysql -u auth_user -p'secure_password' -h localhost secure

# Check MySQL status
sudo systemctl status mysql

# Check MySQL logs
sudo tail -f /var/log/mysql/error.log
```

#### Face Recognition Issues

```bash
# Check DeepFace installation
python -c "import deepface; print('DeepFace OK')"

# Check model files
ls -la ~/.deepface/weights/

# Test with sample images
python -c "from deepface import DeepFace; DeepFace.verify('img1.jpg', 'img2.jpg')"
```

### Performance Issues

```bash
# Monitor system resources
htop
iotop
nethogs

# Check application performance
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:5000/"

# Database performance
mysql -u root -p -e "SHOW PROCESSLIST;"
```

### Security Issues

```bash
# Check for security vulnerabilities
pip install safety
safety check

# Check SSL configuration
openssl s_client -connect your-domain.com:443

# Check firewall status
sudo ufw status
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Weekly tasks
sudo apt update && sudo apt upgrade -y
sudo systemctl restart secure-auth
sudo systemctl restart nginx

# Monthly tasks
sudo certbot renew --dry-run
mysql -u root -p -e "OPTIMIZE TABLE secure.users;"

# Quarterly tasks
# Review and rotate logs
# Update dependencies
# Security audit
```

### Update Process

```bash
# Update application
cd /home/authapp/secure-auth
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart secure-auth

# Update system
sudo apt update && sudo apt upgrade -y
sudo reboot
```

This deployment guide provides comprehensive instructions for deploying the Secure Authentication System in various environments. Choose the deployment method that best fits your requirements and infrastructure.
