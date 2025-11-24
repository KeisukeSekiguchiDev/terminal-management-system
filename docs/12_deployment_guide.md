# デプロイメント手順書
## Terminal Management System (TMS)

**文書バージョン**: 1.0
**作成日**: 2025年11月24日
**対象環境**: AWS (Amazon Web Services)

---

## 1. デプロイメント概要

### 1.1 システム構成

```
┌─────────────────────────────────────────┐
│           AWS Cloud                       │
│                                          │
│  ┌──────────────────────────────┐       │
│  │    Application Load Balancer   │       │
│  └────────────┬─────────────────┘       │
│               │                           │
│  ┌────────────┴─────────────┐           │
│  │     EC2 Auto Scaling      │           │
│  │  ┌────────┐  ┌────────┐  │           │
│  │  │ Django │  │ Django │  │           │
│  │  │  App   │  │  App   │  │           │
│  │  └────────┘  └────────┘  │           │
│  └────────────┬─────────────┘           │
│               │                           │
│  ┌────────────┴─────────────┐           │
│  │      RDS PostgreSQL       │           │
│  │     (Multi-AZ)           │           │
│  └──────────────────────────┘           │
│                                          │
│  ┌──────────────────────────┐           │
│  │       S3 Bucket          │           │
│  │   (Static Files)         │           │
│  └──────────────────────────┘           │
└─────────────────────────────────────────┘
```

### 1.2 必要なAWSサービス

| サービス | 用途 | スペック |
|---------|------|----------|
| EC2 | アプリケーションサーバー | t3.medium x 2台 |
| RDS | データベース | db.t3.medium (PostgreSQL 13) |
| S3 | 静的ファイル配信 | Standard |
| ELB | ロードバランサー | Application LB |
| Route53 | DNS管理 | - |
| CloudWatch | 監視・ログ | - |
| IAM | アクセス管理 | - |

---

## 2. 事前準備

### 2.1 AWSアカウント設定

```bash
# AWS CLIインストール
pip install awscli

# AWS認証情報設定
aws configure
# AWS Access Key ID: [アクセスキー入力]
# AWS Secret Access Key: [シークレットキー入力]
# Default region name: ap-northeast-1
# Default output format: json

# 設定確認
aws sts get-caller-identity
```

### 2.2 必要なツールのインストール

```bash
# Python環境
python --version  # 3.9以上

# Node.js（静的ファイルビルド用）
node --version    # 14以上

# Docker（オプション）
docker --version

# Terraform（Infrastructure as Code）
terraform --version
```

### 2.3 プロジェクト準備

```bash
# リポジトリクローン
git clone https://github.com/techcore/tms.git
cd tms

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envファイルを編集
```

---

## 3. インフラストラクチャ構築

### 3.1 VPCとネットワーク設定

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

### 3.2 RDS（PostgreSQL）セットアップ

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
  password = var.db_password  # terraform.tfvarsで定義

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

### 3.3 EC2インスタンス設定

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

### 3.4 ロードバランサー設定

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

## 4. アプリケーションデプロイ

### 4.1 Djangoアプリケーション設定

```python
# server/tms_server/settings/production.py

import os
from .base import *

# セキュリティ設定
DEBUG = False
ALLOWED_HOSTS = [
    'tms.techcore-solutions.jp',
    '.amazonaws.com',
]

# データベース設定
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

# 静的ファイル設定
STATIC_URL = f"https://{os.environ['S3_BUCKET']}.s3.amazonaws.com/static/"
STATIC_ROOT = '/tmp/static/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# AWS S3設定
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['S3_BUCKET']
AWS_S3_REGION_NAME = 'ap-northeast-1'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_DEFAULT_ACL = None

# セッション設定
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# キャッシュ設定（Redis）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ['REDIS_HOST']}:6379/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ログ設定
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

### 4.2 EC2起動スクリプト

```bash
#!/bin/bash
# userdata.sh

# システム更新
yum update -y

# 必要なパッケージインストール
yum install -y python3 python3-pip git nginx supervisor

# アプリケーションディレクトリ作成
mkdir -p /var/www/tms
cd /var/www/tms

# コードをクローン
git clone https://github.com/techcore/tms.git .

# Python環境セットアップ
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 環境変数設定
cat > /var/www/tms/.env << EOF
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWORD=${db_password}
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DJANGO_SETTINGS_MODULE=tms_server.settings.production
EOF

# データベースマイグレーション
cd server
python manage.py migrate
python manage.py collectstatic --noinput

# Nginxの設定
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

# Supervisorの設定
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

# サービス起動
systemctl start nginx
systemctl enable nginx
supervisorctl reread
supervisorctl update
supervisorctl start tms
```

### 4.3 デプロイ実行

```bash
# Terraformでインフラ構築
cd terraform
terraform init
terraform plan
terraform apply -auto-approve

# データベース初期化
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# 初期データ投入
python manage.py loaddata fixtures/initial_data.json
```

---

## 5. CI/CDパイプライン

### 5.1 GitHub Actions設定

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

### 5.2 Dockerファイル

```dockerfile
# Dockerfile

FROM python:3.9-slim

# 作業ディレクトリ設定
WORKDIR /app

# 依存パッケージインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコピー
COPY server/ .

# 静的ファイル収集
RUN python manage.py collectstatic --noinput

# ポート公開
EXPOSE 8000

# Gunicorn起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "tms_server.wsgi:application"]
```

---

## 6. 監視とロギング

### 6.1 CloudWatch設定

```python
# monitoring/cloudwatch_config.py

import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='ap-northeast-1')

def send_metric(metric_name, value, unit='Count'):
    """カスタムメトリクス送信"""
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

# 使用例
send_metric('ActiveTerminals', Terminal.objects.filter(status='online').count())
send_metric('UnresolvedAlerts', Alert.objects.filter(is_resolved=False).count())
```

### 6.2 アラーム設定

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

## 7. バックアップとリストア

### 7.1 自動バックアップ設定

```bash
# scripts/backup.sh
#!/bin/bash

# 日付取得
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/tms"

# データベースバックアップ
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# S3にアップロード
aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql s3://tms-backups/database/

# 古いバックアップ削除（30日以上）
find $BACKUP_DIR -name "db_backup_*.sql" -mtime +30 -delete

# CloudWatchにメトリクス送信
aws cloudwatch put-metric-data \
  --namespace TMS \
  --metric-name BackupSuccess \
  --value 1 \
  --timestamp $(date -u +%Y-%m-%dT%H:%M:%S)
```

### 7.2 リストア手順

```bash
# データベースリストア
# 1. 最新のバックアップをダウンロード
aws s3 cp s3://tms-backups/database/db_backup_latest.sql ./

# 2. データベースを空にする
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 3. バックアップをリストア
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < db_backup_latest.sql

# 4. アプリケーション再起動
supervisorctl restart tms
```

---

## 8. セキュリティ設定

### 8.1 SSL証明書設定

```bash
# ACM（AWS Certificate Manager）で証明書取得
aws acm request-certificate \
  --domain-name tms.techcore-solutions.jp \
  --validation-method DNS \
  --region ap-northeast-1

# Route53でDNS検証
# ACMコンソールから検証用CNAMEレコードを取得してRoute53に登録
```

### 8.2 WAF設定

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

## 9. 本番環境チェックリスト

### 9.1 デプロイ前確認

- [ ] **コード品質**
  - [ ] 全テストがパス
  - [ ] コードレビュー完了
  - [ ] セキュリティ脆弱性チェック

- [ ] **インフラ**
  - [ ] VPC/サブネット設定完了
  - [ ] セキュリティグループ設定
  - [ ] RDS起動・接続確認

- [ ] **アプリケーション**
  - [ ] 環境変数設定
  - [ ] データベースマイグレーション
  - [ ] 静的ファイル配信確認

- [ ] **監視**
  - [ ] CloudWatchアラーム設定
  - [ ] ログ収集確認
  - [ ] メトリクス送信確認

### 9.2 デプロイ後確認

- [ ] **機能確認**
  - [ ] ログイン機能動作
  - [ ] 主要画面表示
  - [ ] API応答確認

- [ ] **性能確認**
  - [ ] レスポンスタイム測定
  - [ ] 負荷テスト実施
  - [ ] スケーリング動作確認

- [ ] **セキュリティ**
  - [ ] SSL証明書適用
  - [ ] WAF動作確認
  - [ ] アクセス制限確認

---

## 10. トラブルシューティング

### 10.1 よくある問題と対処

| 問題 | 原因 | 対処法 |
|------|------|--------|
| EC2インスタンスが起動しない | User Dataスクリプトエラー | CloudWatchログ確認、スクリプト修正 |
| RDS接続できない | セキュリティグループ設定 | インバウンドルール確認 |
| 502 Bad Gateway | アプリケーション起動失敗 | Gunicornログ確認 |
| 静的ファイル404 | S3バケット設定 | バケットポリシー、CORS確認 |

### 10.2 ロールバック手順

```bash
# 1. 前バージョンのタグ確認
git tag -l

# 2. 前バージョンにロールバック
git checkout v1.0.0

# 3. Dockerイメージビルド・プッシュ
docker build -t tms-app:v1.0.0 .
docker push $ECR_REPOSITORY:v1.0.0

# 4. ECSタスク定義更新
aws ecs register-task-definition \
  --cli-input-json file://task-definition-v1.0.0.json

# 5. サービス更新
aws ecs update-service \
  --cluster tms-cluster \
  --service tms-service \
  --task-definition tms-task:v1.0.0
```

---

## まとめ

このデプロイメント手順に従って：
1. **AWSインフラをTerraformで構築**
2. **Djangoアプリケーションをデプロイ**
3. **CI/CDパイプラインで自動化**
4. **CloudWatchで監視**
5. **定期的なバックアップ実施**

初回デプロイ所要時間: **約2時間**
継続的デプロイ時間: **約10分**