# Beginner's Guide: Start Building Your TMS Now
## Building a Management System for USB Payment Terminal TC-200

**Target Audience**: Programming beginners
**Goal**: Build a working system in 1 month
**Prerequisites**: Windows environment, Python installed

---

## System Overview

### Structure of the System You Will Build

```
[TC-200 Terminal]
    | USB Connection
[Store PC: Windows Agent]
    | Internet (HTTPS)
[Cloud: TMS Management Server]
    | Browser
[Management Console]
```

### Three Required Components

| Component | Role | Technology | Difficulty |
|-----------|------|------------|------------|
| **1. Agent** | Resident program running on store PC | Python | 2/3 |
| **2. TMS Server** | Management system running in cloud | Django | 2/3 |
| **3. Management Console** | Browser-based interface | Django Template | 1/3 |

---

## Week 1: Build Something That Works (Agent Edition)

### Day 1-2: Confirm USB Terminal Communication

**TC-200 DLL Call Sample**

```python
# agent/terminal_controller.py
import ctypes
import json
from datetime import datetime

class TC200Controller:
    def __init__(self, dll_path="TC-200.dll"):
        """Load DLL"""
        try:
            self.dll = ctypes.CDLL(dll_path)
            print(f"DLL loaded successfully: {dll_path}")
        except Exception as e:
            print(f"DLL load failed: {e}")
            self.dll = None

    def get_terminal_info(self):
        """Get terminal information"""
        if not self.dll:
            return {
                "status": "error",
                "message": "DLL not loaded"
            }

        # Call DLL functions (example)
        # Modify according to actual DLL specification
        try:
            # Get serial number (example)
            serial_buffer = ctypes.create_string_buffer(50)
            result = self.dll.GetSerialNumber(serial_buffer)

            if result == 0:  # Success
                return {
                    "status": "online",
                    "serial_number": serial_buffer.value.decode('utf-8'),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "offline",
                    "error_code": result
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

# Test execution
if __name__ == "__main__":
    controller = TC200Controller()
    info = controller.get_terminal_info()
    print(json.dumps(info, indent=2, ensure_ascii=False))
```

### Day 3-4: Communication with TMS Server

**Agent Main Processing**

```python
# agent/main.py
import time
import requests
import json
from terminal_controller import TC200Controller

class TMSAgent:
    def __init__(self):
        self.controller = TC200Controller()
        self.tms_url = "http://localhost:8000/api"  # Test locally first
        self.interval = 60  # Send every 60 seconds

    def send_heartbeat(self):
        """Send status to TMS server"""
        terminal_info = self.controller.get_terminal_info()

        try:
            response = requests.post(
                f"{self.tms_url}/heartbeat",
                json=terminal_info,
                timeout=10
            )

            if response.status_code == 200:
                print(f"Send successful: {terminal_info['serial_number']}")
                # Process commands from server
                commands = response.json().get('commands', [])
                self.process_commands(commands)
            else:
                print(f"Send failed: {response.status_code}")

        except Exception as e:
            print(f"Communication error: {e}")

    def process_commands(self, commands):
        """Execute commands from server"""
        for cmd in commands:
            if cmd['type'] == 'reboot':
                print("Reboot command received")
                # DLL call for terminal reboot
            elif cmd['type'] == 'update_config':
                print("Config update command received")
                # Config update processing

    def run(self):
        """Main loop"""
        print("TMS Agent started")
        while True:
            self.send_heartbeat()
            time.sleep(self.interval)

# Execute
if __name__ == "__main__":
    agent = TMSAgent()
    agent.run()
```

### Day 5: Windows Service Installation

**Auto-start on Windows**

```python
# agent/install_service.py
import sys
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket

class TMSAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TMSAgent"
    _svc_display_name_ = "TMS Agent for TC-200"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Start agent here
        from main import TMSAgent
        agent = TMSAgent()
        agent.run()

if __name__ == '__main__':
    # Install as service
    # python install_service.py install
    # python install_service.py start
    win32serviceutil.HandleCommandLine(TMSAgentService)
```

---

## Week 2: TMS Server Construction (Django Edition)

### Day 6-7: Django Project Creation

**1. Project Initialization**

```bash
# Run in command prompt
pip install django djangorestframework
django-admin startproject tms_server
cd tms_server
python manage.py startapp terminals
```

**2. Model Definition**

```python
# terminals/models.py
from django.db import models

class Terminal(models.Model):
    """Terminal Master"""
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Serial Number'
    )
    store_name = models.CharField(
        max_length=100,
        verbose_name='Store Name',
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('online', 'Online'),
            ('offline', 'Offline'),
            ('error', 'Error'),
        ],
        default='offline',
        verbose_name='Status'
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Heartbeat'
    )
    agent_version = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Agent Version'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )

    class Meta:
        verbose_name = 'Terminal'
        verbose_name_plural = 'Terminals'
        ordering = ['-last_heartbeat']

    def __str__(self):
        return f'{self.serial_number} ({self.store_name})'

class TerminalLog(models.Model):
    """Communication Log"""
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    log_type = models.CharField(max_length=20)  # heartbeat, error, command
    message = models.TextField()

    class Meta:
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'
        ordering = ['-timestamp']
```

### Day 8-9: API Endpoint Creation

```python
# terminals/views.py
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Terminal, TerminalLog

@api_view(['POST'])
def heartbeat(request):
    """Receive heartbeat from agent"""

    serial_number = request.data.get('serial_number')
    terminal_status = request.data.get('status', 'unknown')

    if not serial_number:
        return Response(
            {'error': 'Serial number required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get or create terminal
    terminal, created = Terminal.objects.get_or_create(
        serial_number=serial_number
    )

    # Update status
    terminal.status = terminal_status
    terminal.last_heartbeat = timezone.now()
    terminal.save()

    # Record log
    TerminalLog.objects.create(
        terminal=terminal,
        log_type='heartbeat',
        message=f'Status: {terminal_status}'
    )

    # Response (commands for terminal)
    commands = []

    # If config update is needed
    if terminal.needs_update:  # Add this field later
        commands.append({
            'type': 'update_config',
            'data': {'param1': 'value1'}
        })

    return Response({
        'status': 'ok',
        'commands': commands
    })

def dashboard(request):
    """Management console dashboard"""
    terminals = Terminal.objects.all()

    # Calculate statistics
    stats = {
        'total': terminals.count(),
        'online': terminals.filter(status='online').count(),
        'offline': terminals.filter(status='offline').count(),
        'error': terminals.filter(status='error').count(),
    }

    # Recent logs
    recent_logs = TerminalLog.objects.all()[:20]

    return render(request, 'dashboard.html', {
        'stats': stats,
        'terminals': terminals[:10],  # Latest 10
        'logs': recent_logs
    })
```

### Day 10: Management Console Creation

```html
<!-- templates/dashboard.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TMS Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; }
        .stat-card {
            background: #f0f0f0;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number { font-size: 2em; font-weight: bold; }
        .online { color: green; }
        .offline { color: orange; }
        .error { color: red; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background: #f0f0f0; }
    </style>
    <meta http-equiv="refresh" content="30"> <!-- Auto-refresh every 30 seconds -->
</head>
<body>
    <h1>TMS Dashboard</h1>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-label">Total Terminals</div>
            <div class="stat-number">{{ stats.total }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Online</div>
            <div class="stat-number online">{{ stats.online }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Offline</div>
            <div class="stat-number offline">{{ stats.offline }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Error</div>
            <div class="stat-number error">{{ stats.error }}</div>
        </div>
    </div>

    <h2>Terminal List</h2>
    <table>
        <thead>
            <tr>
                <th>Serial Number</th>
                <th>Store Name</th>
                <th>Status</th>
                <th>Last Heartbeat</th>
            </tr>
        </thead>
        <tbody>
            {% for terminal in terminals %}
            <tr>
                <td>{{ terminal.serial_number }}</td>
                <td>{{ terminal.store_name|default:"-" }}</td>
                <td class="{{ terminal.status }}">{{ terminal.get_status_display }}</td>
                <td>{{ terminal.last_heartbeat|date:"Y-m-d H:i:s"|default:"-" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <h2>Recent Logs</h2>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Terminal</th>
                <th>Type</th>
                <th>Message</th>
            </tr>
        </thead>
        <tbody>
            {% for log in logs %}
            <tr>
                <td>{{ log.timestamp|date:"H:i:s" }}</td>
                <td>{{ log.terminal.serial_number }}</td>
                <td>{{ log.log_type }}</td>
                <td>{{ log.message }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
```

---

## Week 3-4: Making It Practical

### Adding Essential Features

1. **Firmware Updates**
```python
class FirmwareVersion(models.Model):
    version = models.CharField(max_length=20)
    file_url = models.URLField()
    release_date = models.DateTimeField()
    is_latest = models.BooleanField(default=False)

class TerminalCommand(models.Model):
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    command_type = models.CharField(max_length=20)  # update_firmware, reboot, etc
    parameters = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
```

2. **Alert Feature**
```python
def check_offline_terminals():
    """Check offline terminals (run periodically)"""
    from datetime import timedelta
    threshold = timezone.now() - timedelta(minutes=5)

    offline_terminals = Terminal.objects.filter(
        last_heartbeat__lt=threshold,
        status='online'
    )

    for terminal in offline_terminals:
        terminal.status = 'offline'
        terminal.save()
        # Send email
        send_alert_email(terminal)
```

3. **Security Hardening**
```python
# settings.py
ALLOWED_HOSTS = ['your-domain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Agent authentication
class AgentToken(models.Model):
    terminal = models.OneToOneField(Terminal, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## Deploying to Production

### AWS Lightsail (Easiest Method)

```bash
# 1. Create Lightsail instance ($5+/month)
# 2. SSH login
# 3. Environment setup
sudo apt update
sudo apt install python3-pip nginx postgresql

# 4. Upload Django app
git clone your-repo
pip install -r requirements.txt

# 5. Start Gunicorn
gunicorn tms_server.wsgi:application

# 6. Nginx configuration
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

---

## Next Actions You Can Start Immediately

### Do Today

1. **Create folder structure**
```
Terminal Management System/
├── agent/              # Agent (store PC)
│   ├── main.py
│   ├── terminal_controller.py
│   └── requirements.txt
├── server/             # TMS server
│   ├── manage.py
│   ├── tms_server/
│   └── terminals/
└── docs/              # Documentation (already created)
```

2. **First test**
```python
# test_dll.py - Check if DLL can be loaded
import ctypes

try:
    dll = ctypes.CDLL("TC-200.dll")
    print("DLL loaded successfully!")
except Exception as e:
    print(f"Error: {e}")
    print("Please check the DLL file path")
```

3. **Django startup confirmation**
```bash
django-admin startproject test_tms
cd test_tms
python manage.py runserver
# Open http://127.0.0.1:8000 in browser
```

---

## Solutions When You Get Stuck

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| DLL load error | Wrong path | Specify absolute path |
| Django won't start | Port in use | Specify different port: runserver 8001 |
| Cannot communicate | Firewall | Allow in Windows Defender |
| Database error | Migration not run | python manage.py migrate |

### Question Template

When you encounter an error, please provide:
1. What you were trying to do
2. The command you executed
3. Full error message
4. What you've already tried

---

## 1-Week Learning Plan

| Day | Learning Content | Deliverable |
|-----|-----------------|-------------|
| Mon | Python basics review | DLL call test |
| Tue | Django Tutorial Part 1-2 | Project creation |
| Wed | Django Tutorial Part 3-4 | Model creation |
| Thu | Agent creation | Communication test |
| Fri | API creation | Heartbeat endpoint |
| Sat | Screen creation | Dashboard display |
| Sun | Integration test | Agent to server connection |

---

Don't aim for perfection at first - focus on building "something that works."
By adding features one at a time, you will definitely complete it!

If you have questions, I'll answer with specific code examples.
