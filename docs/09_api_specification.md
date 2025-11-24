# API詳細仕様書
## TechCore Solutions TMS

**文書バージョン**: 1.0
**作成日**: 2025年11月24日
**対象**: Devin自動実装用

---

## 1. API基本仕様

### 1.1 基本情報
- **ベースURL**: `https://tms-api.techcore.com/api/v1` (本番)
- **ベースURL**: `http://localhost:8000/api/v1` (開発)
- **プロトコル**: HTTPS (本番) / HTTP (開発)
- **データ形式**: JSON
- **文字コード**: UTF-8
- **認証方式**: Bearer Token
- **タイムアウト**: 30秒

### 1.2 共通ヘッダー

#### リクエストヘッダー
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer {token}
X-Request-ID: {uuid}
X-Terminal-Serial: {serial_number}  # エージェント用
```

#### レスポンスヘッダー
```http
Content-Type: application/json
X-Request-ID: {uuid}
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### 1.3 HTTPステータスコード

| コード | 意味 | 説明 |
|--------|------|------|
| 200 | OK | 成功 |
| 201 | Created | 作成成功 |
| 204 | No Content | 削除成功 |
| 400 | Bad Request | リクエストエラー |
| 401 | Unauthorized | 認証エラー |
| 403 | Forbidden | アクセス権限なし |
| 404 | Not Found | リソースが存在しない |
| 409 | Conflict | 競合（重複など） |
| 422 | Unprocessable Entity | バリデーションエラー |
| 429 | Too Many Requests | レート制限 |
| 500 | Internal Server Error | サーバーエラー |
| 503 | Service Unavailable | メンテナンス中 |

---

## 2. 認証API

### 2.1 ログイン
**POST** `/auth/login`

#### リクエスト
```json
{
    "username": "admin",
    "password": "password123"
}
```

#### レスポンス (200 OK)
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
        "id": 1,
        "username": "admin",
        "full_name": "システム管理者",
        "role": "admin",
        "email": "admin@techcore.com"
    }
}
```

#### エラーレスポンス (401)
```json
{
    "error": {
        "code": "AUTH_001",
        "message": "認証に失敗しました",
        "details": "ユーザー名またはパスワードが正しくありません"
    }
}
```

### 2.2 トークンリフレッシュ
**POST** `/auth/refresh`

#### リクエスト
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### レスポンス (200 OK)
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
}
```

### 2.3 ログアウト
**POST** `/auth/logout`

#### リクエスト
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### レスポンス (204 No Content)
```
(空)
```

---

## 3. エージェント用API

### 3.1 端末登録
**POST** `/agent/register`

#### リクエスト
```json
{
    "serial_number": "TC-200-001",
    "model": "TC-200",
    "mac_address": "00:11:22:33:44:55",
    "agent_version": "1.0.0",
    "hostname": "POS-001",
    "os_info": {
        "name": "Windows",
        "version": "10",
        "build": "19043"
    }
}
```

#### レスポンス (201 Created)
```json
{
    "terminal_id": 123,
    "agent_token": "tk_1234567890abcdef",
    "heartbeat_interval": 300,
    "server_time": "2025-01-24T10:00:00Z",
    "config": {
        "log_level": "INFO",
        "auto_update": true
    }
}
```

### 3.2 ハートビート
**POST** `/agent/heartbeat`

#### リクエスト
```json
{
    "serial_number": "TC-200-001",
    "timestamp": "2025-01-24T10:00:00Z",
    "status": "online",
    "metrics": {
        "cpu_usage": 45,
        "memory_usage": 60,
        "disk_usage": 30,
        "temperature": 35
    },
    "firmware_version": "2.0.0",
    "agent_version": "1.0.0",
    "ip_address": "192.168.1.100",
    "uptime_seconds": 86400,
    "last_transaction": "2025-01-24T09:58:00Z",
    "transaction_count": 150
}
```

#### レスポンス (200 OK)
```json
{
    "status": "acknowledged",
    "server_time": "2025-01-24T10:00:05Z",
    "commands": [
        {
            "id": 456,
            "type": "update_config",
            "priority": "normal",
            "parameters": {
                "heartbeat_interval": 60
            }
        },
        {
            "id": 457,
            "type": "update_firmware",
            "priority": "high",
            "parameters": {
                "version": "2.1.0",
                "url": "https://tms.techcore.com/firmware/TC-200_2.1.0.bin",
                "checksum": "sha256:abcdef1234567890...",
                "size": 10485760
            }
        }
    ],
    "next_heartbeat": 300
}
```

### 3.3 ログ送信
**POST** `/agent/logs`

#### リクエスト
```json
{
    "serial_number": "TC-200-001",
    "logs": [
        {
            "timestamp": "2025-01-24T10:00:00Z",
            "level": "INFO",
            "type": "transaction",
            "message": "Transaction completed successfully",
            "details": {
                "transaction_id": "TRX-123456",
                "amount": 1000,
                "card_type": "VISA"
            }
        },
        {
            "timestamp": "2025-01-24T10:01:00Z",
            "level": "ERROR",
            "type": "communication",
            "message": "Failed to connect to payment gateway",
            "details": {
                "error_code": "NET_001",
                "retry_count": 3
            }
        }
    ]
}
```

#### レスポンス (200 OK)
```json
{
    "status": "received",
    "count": 2,
    "log_ids": [789, 790]
}
```

### 3.4 コマンド実行結果報告
**POST** `/agent/commands/{command_id}/result`

#### リクエスト
```json
{
    "serial_number": "TC-200-001",
    "command_id": 456,
    "status": "completed",
    "started_at": "2025-01-24T10:00:10Z",
    "completed_at": "2025-01-24T10:00:30Z",
    "result": {
        "success": true,
        "message": "Configuration updated successfully"
    }
}
```

#### レスポンス (200 OK)
```json
{
    "status": "acknowledged"
}
```

---

## 4. 管理画面用API

### 4.1 端末一覧取得
**GET** `/terminals`

#### クエリパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| page | integer | No | ページ番号（デフォルト: 1） |
| per_page | integer | No | 1ページあたりの件数（デフォルト: 20、最大: 100） |
| customer_id | integer | No | 顧客IDでフィルタ |
| status | string | No | ステータスでフィルタ（online,offline,error,maintenance） |
| search | string | No | シリアル番号または店舗名で検索 |
| sort | string | No | ソート項目（serial_number,status,last_heartbeat） |
| order | string | No | ソート順（asc,desc） |

#### レスポンス (200 OK)
```json
{
    "data": [
        {
            "id": 123,
            "serial_number": "TC-200-001",
            "customer": {
                "id": 1,
                "company_name": "株式会社ABCストア"
            },
            "store_name": "新宿店",
            "status": "online",
            "firmware_version": "2.0.0",
            "agent_version": "1.0.0",
            "last_heartbeat": "2025-01-24T10:00:00Z",
            "cpu_usage": 45,
            "memory_usage": 60,
            "disk_usage": 30,
            "active_alerts": 0,
            "installed_date": "2024-12-01"
        }
    ],
    "meta": {
        "current_page": 1,
        "per_page": 20,
        "total": 150,
        "total_pages": 8,
        "from": 1,
        "to": 20
    },
    "links": {
        "first": "/api/v1/terminals?page=1",
        "last": "/api/v1/terminals?page=8",
        "prev": null,
        "next": "/api/v1/terminals?page=2"
    }
}
```

### 4.2 端末詳細取得
**GET** `/terminals/{id}`

#### レスポンス (200 OK)
```json
{
    "id": 123,
    "serial_number": "TC-200-001",
    "model": "TC-200",
    "customer": {
        "id": 1,
        "company_name": "株式会社ABCストア",
        "contact_person": "山田太郎",
        "contact_email": "yamada@abc-store.jp",
        "contact_phone": "03-1234-5678",
        "contract_type": "premium"
    },
    "store_name": "新宿店",
    "store_code": "001",
    "installation_address": "東京都新宿区...",
    "status": "online",
    "firmware_version": "2.0.0",
    "agent_version": "1.0.0",
    "ip_address": "192.168.1.100",
    "mac_address": "00:11:22:33:44:55",
    "last_heartbeat": "2025-01-24T10:00:00Z",
    "installed_date": "2024-12-01",
    "warranty_end_date": "2026-12-01",
    "metrics": {
        "cpu_usage": 45,
        "memory_usage": 60,
        "disk_usage": 30,
        "temperature": 35
    },
    "settings": {
        "heartbeat_interval": 300,
        "auto_update_enabled": true,
        "maintenance_mode": false
    },
    "recent_alerts": [
        {
            "id": 789,
            "alert_type": "high_cpu",
            "severity": "WARNING",
            "title": "CPU使用率が高い",
            "created_at": "2025-01-24T09:00:00Z",
            "is_resolved": true
        }
    ],
    "update_history": [
        {
            "id": 456,
            "type": "firmware",
            "from_version": "1.9.0",
            "to_version": "2.0.0",
            "status": "completed",
            "updated_at": "2025-01-20T10:00:00Z"
        }
    ]
}
```

### 4.3 端末設定更新
**PUT** `/terminals/{id}/config`

#### リクエスト
```json
{
    "heartbeat_interval": 60,
    "auto_update_enabled": false,
    "maintenance_mode": true,
    "custom_settings": {
        "log_level": "DEBUG",
        "max_retry": 5
    }
}
```

#### レスポンス (200 OK)
```json
{
    "status": "updated",
    "terminal_id": 123,
    "command_id": 458,
    "message": "設定更新コマンドを送信しました"
}
```

### 4.4 端末コマンド送信
**POST** `/terminals/{id}/commands`

#### リクエスト
```json
{
    "type": "reboot",
    "priority": "high",
    "scheduled_at": "2025-01-24T22:00:00Z",
    "parameters": {
        "force": false,
        "reason": "定期メンテナンス"
    }
}
```

#### レスポンス (201 Created)
```json
{
    "command_id": 459,
    "terminal_id": 123,
    "type": "reboot",
    "status": "pending",
    "scheduled_at": "2025-01-24T22:00:00Z",
    "created_at": "2025-01-24T10:00:00Z"
}
```

### 4.5 アラート一覧取得
**GET** `/alerts`

#### クエリパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| is_resolved | boolean | No | 解決済みフィルタ |
| severity | string | No | 重要度フィルタ（CRITICAL,HIGH,MEDIUM,LOW,INFO） |
| terminal_id | integer | No | 端末IDフィルタ |
| from_date | string | No | 開始日（YYYY-MM-DD） |
| to_date | string | No | 終了日（YYYY-MM-DD） |

#### レスポンス (200 OK)
```json
{
    "data": [
        {
            "id": 789,
            "terminal": {
                "id": 123,
                "serial_number": "TC-200-001",
                "store_name": "新宿店"
            },
            "alert_type": "offline",
            "severity": "HIGH",
            "title": "端末がオフライン",
            "message": "端末 TC-200-001 が5分以上オフラインです",
            "is_acknowledged": false,
            "is_resolved": false,
            "created_at": "2025-01-24T10:00:00Z"
        }
    ],
    "meta": {
        "current_page": 1,
        "total": 15
    }
}
```

### 4.6 アラート更新
**PATCH** `/alerts/{id}`

#### リクエスト
```json
{
    "is_acknowledged": true,
    "is_resolved": true,
    "resolution_notes": "端末を再起動して復旧しました"
}
```

#### レスポンス (200 OK)
```json
{
    "id": 789,
    "status": "resolved",
    "resolved_at": "2025-01-24T10:30:00Z",
    "resolved_by": "operator1"
}
```

---

## 5. レポートAPI

### 5.1 統計サマリー取得
**GET** `/reports/summary`

#### クエリパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| period | string | No | 期間（today,week,month,year） |
| customer_id | integer | No | 顧客IDフィルタ |

#### レスポンス (200 OK)
```json
{
    "period": "month",
    "from_date": "2025-01-01",
    "to_date": "2025-01-24",
    "statistics": {
        "total_terminals": 1234,
        "online_terminals": 1180,
        "offline_terminals": 50,
        "error_terminals": 4,
        "availability_rate": 95.6,
        "total_alerts": 156,
        "resolved_alerts": 145,
        "pending_alerts": 11,
        "average_resolution_time_minutes": 45,
        "total_updates": 23,
        "successful_updates": 22,
        "failed_updates": 1
    },
    "top_issues": [
        {
            "alert_type": "offline",
            "count": 45,
            "percentage": 28.8
        },
        {
            "alert_type": "high_cpu",
            "count": 32,
            "percentage": 20.5
        }
    ],
    "customer_breakdown": [
        {
            "customer_id": 1,
            "company_name": "株式会社ABCストア",
            "total_terminals": 523,
            "online_rate": 96.2
        }
    ]
}
```

### 5.2 稼働率レポート取得
**GET** `/reports/availability`

#### クエリパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| from_date | string | Yes | 開始日（YYYY-MM-DD） |
| to_date | string | Yes | 終了日（YYYY-MM-DD） |
| granularity | string | No | 粒度（hourly,daily,weekly,monthly） |

#### レスポンス (200 OK)
```json
{
    "from_date": "2025-01-01",
    "to_date": "2025-01-24",
    "granularity": "daily",
    "data": [
        {
            "date": "2025-01-24",
            "total_terminals": 1234,
            "online_hours": 28416,
            "total_hours": 29616,
            "availability_rate": 95.9
        }
    ],
    "summary": {
        "average_availability": 96.2,
        "min_availability": 94.5,
        "max_availability": 98.1
    }
}
```

---

## 6. ファームウェア管理API

### 6.1 ファームウェアアップロード
**POST** `/firmware`

#### リクエスト (multipart/form-data)
```
version: 2.1.0
model: TC-200
file: (binary)
release_notes: バグ修正と性能改善
is_mandatory: false
```

#### レスポンス (201 Created)
```json
{
    "id": 10,
    "version": "2.1.0",
    "model": "TC-200",
    "file_name": "TC-200_2.1.0.bin",
    "file_size": 10485760,
    "file_hash": "sha256:abcdef1234567890...",
    "file_url": "https://tms.techcore.com/firmware/TC-200_2.1.0.bin",
    "release_notes": "バグ修正と性能改善",
    "is_mandatory": false,
    "created_at": "2025-01-24T10:00:00Z"
}
```

### 6.2 ファームウェア配信
**POST** `/firmware/{id}/deploy`

#### リクエスト
```json
{
    "target_terminals": "all",  // "all", "customer", "selected"
    "customer_ids": [1, 2, 3],  // target_terminals="customer"の場合
    "terminal_ids": [123, 124, 125],  // target_terminals="selected"の場合
    "schedule": {
        "type": "immediate",  // "immediate", "scheduled", "maintenance_window"
        "start_at": "2025-01-24T22:00:00Z",
        "batch_size": 10,
        "interval_minutes": 5
    },
    "rollback_on_failure": true,
    "max_failure_rate": 10
}
```

#### レスポンス (201 Created)
```json
{
    "deployment_id": 50,
    "firmware_id": 10,
    "total_terminals": 100,
    "status": "scheduled",
    "scheduled_at": "2025-01-24T22:00:00Z",
    "estimated_completion": "2025-01-25T00:00:00Z"
}
```

---

## 7. WebSocket API

### 7.1 リアルタイム監視
**WebSocket** `/ws/monitoring`

#### 接続確立
```javascript
const ws = new WebSocket('wss://tms.techcore.com/ws/monitoring');
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    }));
};
```

#### サーバーからのメッセージ
```json
{
    "type": "terminal_status_change",
    "data": {
        "terminal_id": 123,
        "serial_number": "TC-200-001",
        "old_status": "online",
        "new_status": "offline",
        "timestamp": "2025-01-24T10:00:00Z"
    }
}
```

```json
{
    "type": "new_alert",
    "data": {
        "alert_id": 790,
        "terminal_id": 123,
        "severity": "HIGH",
        "title": "端末がオフライン",
        "message": "端末 TC-200-001 が応答しません"
    }
}
```

#### クライアントからのメッセージ
```json
{
    "type": "subscribe",
    "channels": ["terminals", "alerts", "updates"]
}
```

---

## 8. エラーハンドリング

### 8.1 エラーレスポンス形式

```json
{
    "error": {
        "code": "ERR_001",
        "message": "エラーが発生しました",
        "details": "詳細なエラー情報",
        "field_errors": {
            "email": ["有効なメールアドレスを入力してください"],
            "password": ["8文字以上で入力してください"]
        },
        "request_id": "req_1234567890",
        "timestamp": "2025-01-24T10:00:00Z"
    }
}
```

### 8.2 エラーコード一覧

| コード | HTTPステータス | 説明 | 対処法 |
|--------|---------------|------|--------|
| AUTH_001 | 401 | 認証失敗 | ユーザー名とパスワードを確認 |
| AUTH_002 | 401 | トークン期限切れ | リフレッシュトークンで更新 |
| AUTH_003 | 403 | 権限不足 | 必要な権限を確認 |
| VAL_001 | 422 | バリデーションエラー | field_errorsを確認 |
| VAL_002 | 409 | 重複エラー | 既存データを確認 |
| RES_001 | 404 | リソースが見つからない | IDを確認 |
| RATE_001 | 429 | レート制限超過 | 時間をおいて再試行 |
| SYS_001 | 500 | サーバーエラー | サポートに連絡 |
| SYS_002 | 503 | メンテナンス中 | メンテナンス終了を待つ |

---

## 9. レート制限

### 9.1 制限値

| エンドポイント | 制限 | ウィンドウ |
|---------------|------|-----------|
| /auth/* | 10 requests | 1分 |
| /agent/heartbeat | 1 request | 30秒 |
| /agent/logs | 100 requests | 1分 |
| その他API | 1000 requests | 1分 |

### 9.2 レート制限超過時のレスポンス

```json
{
    "error": {
        "code": "RATE_001",
        "message": "レート制限を超過しました",
        "details": "1分後に再試行してください",
        "retry_after": 60
    }
}
```

---

## 10. 実装例（Python）

### 10.1 エージェント実装例

```python
import requests
import json
import time
from datetime import datetime

class TMSAgent:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.token = None
        self.serial_number = "TC-200-001"

    def register(self):
        """端末登録"""
        url = f"{self.base_url}/agent/register"
        data = {
            "serial_number": self.serial_number,
            "model": "TC-200",
            "mac_address": "00:11:22:33:44:55",
            "agent_version": "1.0.0"
        }
        response = requests.post(url, json=data)
        if response.status_code == 201:
            result = response.json()
            self.token = result["agent_token"]
            return result
        else:
            raise Exception(f"Registration failed: {response.text}")

    def send_heartbeat(self):
        """ハートビート送信"""
        url = f"{self.base_url}/agent/heartbeat"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Terminal-Serial": self.serial_number
        }
        data = {
            "serial_number": self.serial_number,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "online",
            "metrics": {
                "cpu_usage": 45,
                "memory_usage": 60,
                "disk_usage": 30
            }
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Heartbeat failed: {response.text}")

    def run(self):
        """メインループ"""
        # 登録
        print("Registering terminal...")
        reg_result = self.register()
        print(f"Registered: Terminal ID = {reg_result['terminal_id']}")

        # ハートビートループ
        interval = reg_result.get('heartbeat_interval', 300)
        while True:
            try:
                print("Sending heartbeat...")
                result = self.send_heartbeat()

                # コマンド処理
                if result.get('commands'):
                    for command in result['commands']:
                        self.process_command(command)

                # 次回送信まで待機
                interval = result.get('next_heartbeat', interval)
                time.sleep(interval)

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)  # エラー時は60秒後に再試行

    def process_command(self, command):
        """コマンド処理"""
        print(f"Processing command: {command['type']}")
        # コマンドタイプに応じた処理
        if command['type'] == 'reboot':
            self.reboot()
        elif command['type'] == 'update_config':
            self.update_config(command['parameters'])
        # 結果報告
        self.report_command_result(command['id'], 'completed')

    def report_command_result(self, command_id, status):
        """コマンド実行結果報告"""
        url = f"{self.base_url}/agent/commands/{command_id}/result"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Terminal-Serial": self.serial_number
        }
        data = {
            "serial_number": self.serial_number,
            "command_id": command_id,
            "status": status,
            "completed_at": datetime.utcnow().isoformat() + "Z"
        }
        requests.post(url, json=data, headers=headers)

if __name__ == "__main__":
    agent = TMSAgent()
    agent.run()
```

### 10.2 管理画面API呼び出し例

```python
import requests

class TMSClient:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.token = None

    def login(self, username, password):
        """ログイン"""
        url = f"{self.base_url}/auth/login"
        response = requests.post(url, json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            return data
        else:
            raise Exception("Login failed")

    def get_terminals(self, page=1, status=None):
        """端末一覧取得"""
        url = f"{self.base_url}/terminals"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"page": page}
        if status:
            params["status"] = status

        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def get_terminal_detail(self, terminal_id):
        """端末詳細取得"""
        url = f"{self.base_url}/terminals/{terminal_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers)
        return response.json()

    def send_command(self, terminal_id, command_type, parameters=None):
        """コマンド送信"""
        url = f"{self.base_url}/terminals/{terminal_id}/commands"
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "type": command_type,
            "priority": "normal",
            "parameters": parameters or {}
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()

# 使用例
client = TMSClient()
client.login("admin", "password123")

# 端末一覧取得
terminals = client.get_terminals(status="online")
print(f"オンライン端末数: {terminals['meta']['total']}")

# 端末詳細取得
detail = client.get_terminal_detail(123)
print(f"端末 {detail['serial_number']}: {detail['status']}")

# 再起動コマンド送信
result = client.send_command(123, "reboot")
print(f"コマンドID {result['command_id']} を送信しました")
```

---

この仕様書に基づいて、Devinが自動的にAPIを実装できます。