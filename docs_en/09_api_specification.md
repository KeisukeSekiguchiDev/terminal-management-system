# API Detailed Specification Document
## TechCore Solutions TMS

**Document Version**: 1.0
**Created**: November 24, 2025
**Target**: Devin Auto-implementation

---

## 1. API Basic Specifications

### 1.1 Basic Information
- **Base URL**: `https://tms-api.techcore.com/api/v1` (Production)
- **Base URL**: `http://localhost:8000/api/v1` (Development)
- **Protocol**: HTTPS (Production) / HTTP (Development)
- **Data Format**: JSON
- **Character Encoding**: UTF-8
- **Authentication**: Bearer Token
- **Timeout**: 30 seconds

### 1.2 Common Headers

#### Request Headers
```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer {token}
X-Request-ID: {uuid}
X-Terminal-Serial: {serial_number}  # For agent
```

#### Response Headers
```http
Content-Type: application/json
X-Request-ID: {uuid}
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### 1.3 HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Success |
| 201 | Created | Creation successful |
| 204 | No Content | Deletion successful |
| 400 | Bad Request | Request error |
| 401 | Unauthorized | Authentication error |
| 403 | Forbidden | No access permission |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Conflict (duplicate, etc.) |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Under maintenance |

---

## 2. Authentication API

### 2.1 Login
**POST** `/auth/login`

#### Request
```json
{
    "username": "admin",
    "password": "password123"
}
```

#### Response (200 OK)
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
        "id": 1,
        "username": "admin",
        "full_name": "System Administrator",
        "role": "admin",
        "email": "admin@techcore.com"
    }
}
```

#### Error Response (401)
```json
{
    "error": {
        "code": "AUTH_001",
        "message": "Authentication failed",
        "details": "Username or password is incorrect"
    }
}
```

### 2.2 Token Refresh
**POST** `/auth/refresh`

#### Request
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response (200 OK)
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
}
```

### 2.3 Logout
**POST** `/auth/logout`

#### Request
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response (204 No Content)
```
(empty)
```

---

## 3. Agent API

### 3.1 Terminal Registration
**POST** `/agent/register`

#### Request
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

#### Response (201 Created)
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

### 3.2 Heartbeat
**POST** `/agent/heartbeat`

#### Request
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

#### Response (200 OK)
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

### 3.3 Log Submission
**POST** `/agent/logs`

#### Request
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

#### Response (200 OK)
```json
{
    "status": "received",
    "count": 2,
    "log_ids": [789, 790]
}
```

### 3.4 Command Execution Result Report
**POST** `/agent/commands/{command_id}/result`

#### Request
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

#### Response (200 OK)
```json
{
    "status": "acknowledged"
}
```

---

## 4. Admin Panel API

### 4.1 Get Terminal List
**GET** `/terminals`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| per_page | integer | No | Items per page (default: 20, max: 100) |
| customer_id | integer | No | Filter by customer ID |
| status | string | No | Filter by status (online,offline,error,maintenance) |
| search | string | No | Search by serial number or store name |
| sort | string | No | Sort field (serial_number,status,last_heartbeat) |
| order | string | No | Sort order (asc,desc) |

#### Response (200 OK)
```json
{
    "data": [
        {
            "id": 123,
            "serial_number": "TC-200-001",
            "customer": {
                "id": 1,
                "company_name": "ABC Store Inc."
            },
            "store_name": "Shinjuku Store",
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

### 4.2 Get Terminal Details
**GET** `/terminals/{id}`

#### Response (200 OK)
```json
{
    "id": 123,
    "serial_number": "TC-200-001",
    "model": "TC-200",
    "customer": {
        "id": 1,
        "company_name": "ABC Store Inc.",
        "contact_person": "Taro Yamada",
        "contact_email": "yamada@abc-store.jp",
        "contact_phone": "03-1234-5678",
        "contract_type": "premium"
    },
    "store_name": "Shinjuku Store",
    "store_code": "001",
    "installation_address": "Shinjuku-ku, Tokyo...",
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
            "title": "High CPU Usage",
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

### 4.3 Update Terminal Configuration
**PUT** `/terminals/{id}/config`

#### Request
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

#### Response (200 OK)
```json
{
    "status": "updated",
    "terminal_id": 123,
    "command_id": 458,
    "message": "Configuration update command sent"
}
```

### 4.4 Send Terminal Command
**POST** `/terminals/{id}/commands`

#### Request
```json
{
    "type": "reboot",
    "priority": "high",
    "scheduled_at": "2025-01-24T22:00:00Z",
    "parameters": {
        "force": false,
        "reason": "Scheduled maintenance"
    }
}
```

#### Response (201 Created)
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

### 4.5 Get Alert List
**GET** `/alerts`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| is_resolved | boolean | No | Filter by resolved status |
| severity | string | No | Filter by severity (CRITICAL,HIGH,MEDIUM,LOW,INFO) |
| terminal_id | integer | No | Filter by terminal ID |
| from_date | string | No | Start date (YYYY-MM-DD) |
| to_date | string | No | End date (YYYY-MM-DD) |

#### Response (200 OK)
```json
{
    "data": [
        {
            "id": 789,
            "terminal": {
                "id": 123,
                "serial_number": "TC-200-001",
                "store_name": "Shinjuku Store"
            },
            "alert_type": "offline",
            "severity": "HIGH",
            "title": "Terminal Offline",
            "message": "Terminal TC-200-001 has been offline for more than 5 minutes",
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

### 4.6 Update Alert
**PATCH** `/alerts/{id}`

#### Request
```json
{
    "is_acknowledged": true,
    "is_resolved": true,
    "resolution_notes": "Resolved by rebooting the terminal"
}
```

#### Response (200 OK)
```json
{
    "id": 789,
    "status": "resolved",
    "resolved_at": "2025-01-24T10:30:00Z",
    "resolved_by": "operator1"
}
```

---

## 5. Report API

### 5.1 Get Statistics Summary
**GET** `/reports/summary`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| period | string | No | Period (today,week,month,year) |
| customer_id | integer | No | Filter by customer ID |

#### Response (200 OK)
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
            "company_name": "ABC Store Inc.",
            "total_terminals": 523,
            "online_rate": 96.2
        }
    ]
}
```

### 5.2 Get Availability Report
**GET** `/reports/availability`

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| from_date | string | Yes | Start date (YYYY-MM-DD) |
| to_date | string | Yes | End date (YYYY-MM-DD) |
| granularity | string | No | Granularity (hourly,daily,weekly,monthly) |

#### Response (200 OK)
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

## 6. Firmware Management API

### 6.1 Upload Firmware
**POST** `/firmware`

#### Request (multipart/form-data)
```
version: 2.1.0
model: TC-200
file: (binary)
release_notes: Bug fixes and performance improvements
is_mandatory: false
```

#### Response (201 Created)
```json
{
    "id": 10,
    "version": "2.1.0",
    "model": "TC-200",
    "file_name": "TC-200_2.1.0.bin",
    "file_size": 10485760,
    "file_hash": "sha256:abcdef1234567890...",
    "file_url": "https://tms.techcore.com/firmware/TC-200_2.1.0.bin",
    "release_notes": "Bug fixes and performance improvements",
    "is_mandatory": false,
    "created_at": "2025-01-24T10:00:00Z"
}
```

### 6.2 Deploy Firmware
**POST** `/firmware/{id}/deploy`

#### Request
```json
{
    "target_terminals": "all",  // "all", "customer", "selected"
    "customer_ids": [1, 2, 3],  // When target_terminals="customer"
    "terminal_ids": [123, 124, 125],  // When target_terminals="selected"
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

#### Response (201 Created)
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

### 7.1 Real-time Monitoring
**WebSocket** `/ws/monitoring`

#### Connection Establishment
```javascript
const ws = new WebSocket('wss://tms.techcore.com/ws/monitoring');
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    }));
};
```

#### Server Messages
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
        "title": "Terminal Offline",
        "message": "Terminal TC-200-001 is not responding"
    }
}
```

#### Client Messages
```json
{
    "type": "subscribe",
    "channels": ["terminals", "alerts", "updates"]
}
```

---

## 8. Error Handling

### 8.1 Error Response Format

```json
{
    "error": {
        "code": "ERR_001",
        "message": "An error occurred",
        "details": "Detailed error information",
        "field_errors": {
            "email": ["Please enter a valid email address"],
            "password": ["Must be at least 8 characters"]
        },
        "request_id": "req_1234567890",
        "timestamp": "2025-01-24T10:00:00Z"
    }
}
```

### 8.2 Error Code List

| Code | HTTP Status | Description | Resolution |
|------|-------------|-------------|------------|
| AUTH_001 | 401 | Authentication failed | Check username and password |
| AUTH_002 | 401 | Token expired | Refresh with refresh token |
| AUTH_003 | 403 | Insufficient permissions | Check required permissions |
| VAL_001 | 422 | Validation error | Check field_errors |
| VAL_002 | 409 | Duplicate error | Check existing data |
| RES_001 | 404 | Resource not found | Check ID |
| RATE_001 | 429 | Rate limit exceeded | Retry after waiting |
| SYS_001 | 500 | Server error | Contact support |
| SYS_002 | 503 | Under maintenance | Wait for maintenance completion |

---

## 9. Rate Limiting

### 9.1 Limit Values

| Endpoint | Limit | Window |
|----------|-------|--------|
| /auth/* | 10 requests | 1 minute |
| /agent/heartbeat | 1 request | 30 seconds |
| /agent/logs | 100 requests | 1 minute |
| Other APIs | 1000 requests | 1 minute |

### 9.2 Rate Limit Exceeded Response

```json
{
    "error": {
        "code": "RATE_001",
        "message": "Rate limit exceeded",
        "details": "Please retry after 1 minute",
        "retry_after": 60
    }
}
```

---

## 10. Implementation Examples (Python)

### 10.1 Agent Implementation Example

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
        """Terminal registration"""
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
        """Send heartbeat"""
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
        """Main loop"""
        # Registration
        print("Registering terminal...")
        reg_result = self.register()
        print(f"Registered: Terminal ID = {reg_result['terminal_id']}")

        # Heartbeat loop
        interval = reg_result.get('heartbeat_interval', 300)
        while True:
            try:
                print("Sending heartbeat...")
                result = self.send_heartbeat()

                # Command processing
                if result.get('commands'):
                    for command in result['commands']:
                        self.process_command(command)

                # Wait until next transmission
                interval = result.get('next_heartbeat', interval)
                time.sleep(interval)

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)  # Retry after 60 seconds on error

    def process_command(self, command):
        """Process command"""
        print(f"Processing command: {command['type']}")
        # Process based on command type
        if command['type'] == 'reboot':
            self.reboot()
        elif command['type'] == 'update_config':
            self.update_config(command['parameters'])
        # Report result
        self.report_command_result(command['id'], 'completed')

    def report_command_result(self, command_id, status):
        """Report command execution result"""
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

### 10.2 Admin Panel API Call Example

```python
import requests

class TMSClient:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.token = None

    def login(self, username, password):
        """Login"""
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
        """Get terminal list"""
        url = f"{self.base_url}/terminals"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"page": page}
        if status:
            params["status"] = status

        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def get_terminal_detail(self, terminal_id):
        """Get terminal details"""
        url = f"{self.base_url}/terminals/{terminal_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers)
        return response.json()

    def send_command(self, terminal_id, command_type, parameters=None):
        """Send command"""
        url = f"{self.base_url}/terminals/{terminal_id}/commands"
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "type": command_type,
            "priority": "normal",
            "parameters": parameters or {}
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()

# Usage example
client = TMSClient()
client.login("admin", "password123")

# Get terminal list
terminals = client.get_terminals(status="online")
print(f"Online terminals: {terminals['meta']['total']}")

# Get terminal details
detail = client.get_terminal_detail(123)
print(f"Terminal {detail['serial_number']}: {detail['status']}")

# Send reboot command
result = client.send_command(123, "reboot")
print(f"Sent command ID {result['command_id']}")
```

---

Devin can automatically implement the API based on this specification document.
