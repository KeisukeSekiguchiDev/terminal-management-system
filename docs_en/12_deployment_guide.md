# Deployment Guide
## Terminal Management System (TMS)

**Document Version**: 1.0
**Created Date**: November 24, 2025
**Target Environment**: AWS (Amazon Web Services)

---

## 1. Deployment Overview

### 1.1 System Architecture

```
+-----------------------------------------+
|           AWS Cloud                      |
|                                          |
|  +------------------------------+        |
|  |    Application Load Balancer  |        |
|  +--------------+---------------+        |
|                 |                        |
|  +--------------+--------------+         |
|  |     EC2 Auto Scaling         |         |
|  |  +--------+  +--------+     |         |
|  |  | Django |  | Django |     |         |
|  |  |  App   |  |  App   |     |         |
|  |  +--------+  +--------+     |         |
|  +--------------+--------------+         |
|                 |                        |
|  +--------------+--------------+         |
|  |      RDS PostgreSQL          |         |
|  |     (Multi-AZ)               |         |
|  +------------------------------+         |
|                                          |
|  +------------------------------+         |
|  |       S3 Bucket               |         |
|  |   (Static Files)              |         |
|  +------------------------------+         |
+-----------------------------------------+
```

### 1.2 Required AWS Services

| Service | Purpose | Specification |
|---------|---------|---------------|
| EC2 | Application server | t3.medium x 2 instances |
| RDS | Database | db.t3.medium (PostgreSQL 13) |
| S3 | Static file delivery | Standard |
| ELB | Load balancer | Application LB |
| Route53 | DNS management | - |
| CloudWatch | Monitoring/logging | - |
| IAM | Access management | - |

---

## 2. Prerequisites

### 2.1 AWS Account Configuration

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure
# AWS Access Key ID: [Enter access key]
# AWS Secret Access Key: [Enter secret key]
# Default region name: ap-northeast-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### 2.2 Installing Required Tools

```bash
# Python environment
python --version  # 3.9 or higher

# Node.js (for static file build)
node --version    # 14 or higher

# Docker (optional)
docker --version

# Terraform (Infrastructure as Code)
terraform --version
```

### 2.3 Project Preparation

```bash
# Clone repository
git clone https://github.com/techcore/tms.git
cd tms

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit the .env file
```

---

## 3. Infrastructure Setup

### 3.1 VPC and Network Configuration

```bash
# terraform/vpc.tf

resource "aws_vpc" "tms_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "tms-vpc"
  }
}

resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.tms_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "tms-public-subnet-1"
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.tms_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "ap-northeast-1c"
  map_public_ip_on_launch = true

  tags = {
    Name = "tms-public-subnet-2"
  }
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.tms_vpc.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "ap-northeast-1a"

  tags = {
    Name = "tms-private-subnet-1"
  }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.tms_vpc.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "ap-northeast-1c"

  tags = {
    Name = "tms-private-subnet-2"
  }
}
```

### 3.2 RDS (PostgreSQL) Setup

```bash
# terraform/rds.tf

resource "aws_db_instance" "tms_db" {
  identifier     = "tms-database"
  engine         = "postgres"
  engine_version = "13.7"
  instance_class = "db.t3.medium"

  allocated_storage     = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "tms_production"
  username = "tms_admin"
  password = var.db_password  # Define in terraform.tfvars

  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.tms_db_subnet.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az               = true
  publicly_accessible    = false
  deletion_protection    = true

  tags = {
    Name = "tms-production-db"
  }
}

resource "aws_security_group" "db_sg" {
  name        = "tms-db-security-group"
  description = "Security group for TMS database"
  vpc_id      = aws_vpc.tms_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### 3.3 EC2 Instance Configuration

```bash
# terraform/ec2.tf

resource "aws_launch_template" "tms_app" {
  name_prefix   = "tms-app-"
  image_id      = "ami-0ab3794db9457b60a"  # Amazon Linux 2
  instance_type = "t3.medium"

  user_data = base64encode(templatefile("userdata.sh", {
    db_host     = aws_db_instance.tms_db.endpoint
    db_name     = "tms_production"
    db_user     = "tms_admin"
    db_password = var.db_password
  }))

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "tms-app-server"
    }
  }
}

resource "aws_autoscaling_group" "tms_asg" {
  name                = "tms-autoscaling-group"
  vpc_zone_identifier = [
    aws_subnet.private_subnet_1.id,
    aws_subnet.private_subnet_2.id
  ]

  target_group_arns = [aws_lb_target_group.tms_tg.arn]
  health_check_type = "ELB"
  health_check_grace_period = 300

  min_size         = 2
  max_size         = 10
  desired_capacity = 2

  launch_template {
    id      = aws_launch_template.tms_app.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "tms-app-instance"
    propagate_at_launch = true
  }
}
```

### 3.4 Load Balancer Configuration

```bash
# terraform/alb.tf

resource "aws_lb" "tms_alb" {
  name               = "tms-application-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets           = [
    aws_subnet.public_subnet_1.id,
    aws_subnet.public_subnet_2.id
  ]

  tags = {
    Name = "tms-alb"
  }
}

resource "aws_lb_target_group" "tms_tg" {
  name     = "tms-target-group"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.tms_vpc.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health/"
    matcher             = "200"
  }
}

resource "aws_lb_listener" "tms_listener" {
  load_balancer_arn = aws_lb.tms_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.ssl_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tms_tg.arn
  }
}
```

---

## 4. Application Deployment

### 4.1 Django Application Configuration

```python
# server/tms_server/settings/production.py

import os
from .base import *

# Security settings
DEBUG = False
ALLOWED_HOSTS = [
    'tms.techcore-solutions.jp',
    '.amazonaws.com',
]

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Static file settings
STATIC_URL = f"https://{os.environ['S3_BUCKET']}.s3.amazonaws.com/static/"
STATIC_ROOT = '/tmp/static/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# AWS S3 settings
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['S3_BUCKET']
AWS_S3_REGION_NAME = 'ap-northeast-1'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_DEFAULT_ACL = None

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Cache settings (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ['REDIS_HOST']}:6379/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Logging settings
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/tms/django_error.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 10,
        },
        'cloudwatch': {
            'level': 'INFO',
            'class': 'watchtower.CloudWatchLogHandler',
            'log_group': 'tms-application',
            'stream_name': 'django',
        },
    },
    'root': {
        'handlers': ['file', 'cloudwatch'],
        'level': 'INFO',
    },
}
```

### 4.2 EC2 Startup Script

```bash
#!/bin/bash
# userdata.sh

# System update
yum update -y

# Install required packages
yum install -y python3 python3-pip git nginx supervisor

# Create application directory
mkdir -p /var/www/tms
cd /var/www/tms

# Clone code
git clone https://github.com/techcore/tms.git .

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Configure environment variables
cat > /var/www/tms/.env << EOF
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWORD=${db_password}
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DJANGO_SETTINGS_MODULE=tms_server.settings.production
EOF

# Database migration
cd server
python manage.py migrate
python manage.py collectstatic --noinput

# Nginx configuration
cat > /etc/nginx/conf.d/tms.conf << 'EOF'
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /var/www/tms/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Supervisor configuration
cat > /etc/supervisor/conf.d/tms.conf << 'EOF'
[program:tms]
command=/var/www/tms/venv/bin/gunicorn tms_server.wsgi:application --bind 127.0.0.1:8000 --workers 4
directory=/var/www/tms/server
user=nginx
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tms/gunicorn.log
environment=PATH="/var/www/tms/venv/bin"
EOF

# Start services
systemctl start nginx
systemctl enable nginx
supervisorctl reread
supervisorctl update
supervisorctl start tms
```

### 4.3 Deployment Execution

```bash
# Build infrastructure with Terraform
cd terraform
terraform init
terraform plan
terraform apply -auto-approve

# Database initialization
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# Load initial data
python manage.py loaddata fixtures/initial_data.json
```

---

## 5. CI/CD Pipeline

### 5.1 GitHub Actions Configuration

```yaml
# .github/workflows/deploy.yml

name: Deploy to AWS

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests
      run: |
        python manage.py test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v2

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-northeast-1

    - name: Build and push Docker image
      run: |
        docker build -t tms-app .
        docker tag tms-app:latest ${{ secrets.ECR_REPOSITORY }}:latest
        docker push ${{ secrets.ECR_REPOSITORY }}:latest

    - name: Deploy to ECS
      run: |
        aws ecs update-service \
          --cluster tms-cluster \
          --service tms-service \
          --force-new-deployment
```

### 5.2 Dockerfile

```dockerfile
# Dockerfile

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server/ .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "tms_server.wsgi:application"]
```

---

## 6. Monitoring and Logging

### 6.1 CloudWatch Configuration

```python
# monitoring/cloudwatch_config.py

import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='ap-northeast-1')

def send_metric(metric_name, value, unit='Count'):
    """Send custom metrics"""
    cloudwatch.put_metric_data(
        Namespace='TMS',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# Usage examples
send_metric('ActiveTerminals', Terminal.objects.filter(status='online').count())
send_metric('UnresolvedAlerts', Alert.objects.filter(is_resolved=False).count())
```

### 6.2 Alarm Configuration

```bash
# terraform/cloudwatch_alarms.tf

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "tms-high-cpu-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.tms_asg.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "tms-low-db-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10737418240"  # 10GB

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.tms_db.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

---

## 7. Backup and Restore

### 7.1 Automatic Backup Configuration

```bash
# scripts/backup.sh
#!/bin/bash

# Get date
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/tms"

# Database backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Upload to S3
aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql s3://tms-backups/database/

# Delete old backups (older than 30 days)
find $BACKUP_DIR -name "db_backup_*.sql" -mtime +30 -delete

# Send metrics to CloudWatch
aws cloudwatch put-metric-data \
  --namespace TMS \
  --metric-name BackupSuccess \
  --value 1 \
  --timestamp $(date -u +%Y-%m-%dT%H:%M:%S)
```

### 7.2 Restore Procedure

```bash
# Database restore
# 1. Download latest backup
aws s3 cp s3://tms-backups/database/db_backup_latest.sql ./

# 2. Empty the database
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 3. Restore from backup
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < db_backup_latest.sql

# 4. Restart application
supervisorctl restart tms
```

---

## 8. Security Configuration

### 8.1 SSL Certificate Configuration

```bash
# Obtain certificate with ACM (AWS Certificate Manager)
aws acm request-certificate \
  --domain-name tms.techcore-solutions.jp \
  --validation-method DNS \
  --region ap-northeast-1

# DNS validation with Route53
# Obtain validation CNAME record from ACM console and add to Route53
```

### 8.2 WAF Configuration

```bash
# terraform/waf.tf

resource "aws_wafv2_web_acl" "tms_waf" {
  name  = "tms-web-acl"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimitRule"
    priority = 1

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    action {
      block {}
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "tms-waf"
    sampled_requests_enabled   = true
  }
}
```

---

## 9. Production Environment Checklist

### 9.1 Pre-deployment Verification

- [ ] **Code Quality**
  - [ ] All tests pass
  - [ ] Code review completed
  - [ ] Security vulnerability check

- [ ] **Infrastructure**
  - [ ] VPC/subnet configuration complete
  - [ ] Security group configuration
  - [ ] RDS startup/connection verification

- [ ] **Application**
  - [ ] Environment variables configured
  - [ ] Database migration
  - [ ] Static file delivery verification

- [ ] **Monitoring**
  - [ ] CloudWatch alarms configured
  - [ ] Log collection verification
  - [ ] Metrics transmission verification

### 9.2 Post-deployment Verification

- [ ] **Functionality Verification**
  - [ ] Login function works
  - [ ] Main screens display
  - [ ] API response verification

- [ ] **Performance Verification**
  - [ ] Response time measurement
  - [ ] Load test execution
  - [ ] Scaling operation verification

- [ ] **Security**
  - [ ] SSL certificate applied
  - [ ] WAF operation verification
  - [ ] Access restriction verification

---

## 10. Troubleshooting

### 10.1 Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| EC2 instance won't start | User Data script error | Check CloudWatch logs, fix script |
| Cannot connect to RDS | Security group configuration | Check inbound rules |
| 502 Bad Gateway | Application startup failure | Check Gunicorn logs |
| Static file 404 | S3 bucket configuration | Check bucket policy, CORS |

### 10.2 Rollback Procedure

```bash
# 1. Check previous version tag
git tag -l

# 2. Rollback to previous version
git checkout v1.0.0

# 3. Build and push Docker image
docker build -t tms-app:v1.0.0 .
docker push $ECR_REPOSITORY:v1.0.0

# 4. Update ECS task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition-v1.0.0.json

# 5. Update service
aws ecs update-service \
  --cluster tms-cluster \
  --service tms-service \
  --task-definition tms-task:v1.0.0
```

---

## Summary

Following this deployment guide:
1. **Build AWS infrastructure with Terraform**
2. **Deploy Django application**
3. **Automate with CI/CD pipeline**
4. **Monitor with CloudWatch**
5. **Perform regular backups**

Initial deployment time: **Approximately 2 hours**
Continuous deployment time: **Approximately 10 minutes**
