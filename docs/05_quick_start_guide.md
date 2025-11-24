# 初心者向け：TMSを今すぐ作り始めるガイド
## USB決済端末TC-200の管理システム構築

**対象**: プログラミング初心者
**目標**: 1ヶ月で動くものを作る
**前提**: Windows環境、Python導入済み

---

## 🎯 システム全体像の理解

### あなたが作るシステムの構成

```
[TC-200端末]
    ↓ USB接続
[店舗PC：Windowsエージェント]
    ↓ インターネット（HTTPS）
[クラウド：TMS管理サーバー]
    ↓ ブラウザ
[管理画面]
```

### 必要な3つのコンポーネント

| コンポーネント | 役割 | 技術 | 難易度 |
|--------------|------|------|--------|
| **1. エージェント** | 店舗PCで動く常駐プログラム | Python | ★★☆ |
| **2. TMSサーバー** | クラウドで動く管理システム | Django | ★★☆ |
| **3. 管理画面** | ブラウザで見る画面 | Django Template | ★☆☆ |

---

## 📝 Week 1: まず動くものを作る（エージェント編）

### Day 1-2: USB端末との通信確認

**TC-200のDLL呼び出しサンプル**

```python
# agent/terminal_controller.py
import ctypes
import json
from datetime import datetime

class TC-200Controller:
    def __init__(self, dll_path="TC-200.dll"):
        """DLLを読み込む"""
        try:
            self.dll = ctypes.CDLL(dll_path)
            print(f"✅ DLL読み込み成功: {dll_path}")
        except Exception as e:
            print(f"❌ DLL読み込み失敗: {e}")
            self.dll = None

    def get_terminal_info(self):
        """端末情報を取得"""
        if not self.dll:
            return {
                "status": "error",
                "message": "DLL not loaded"
            }

        # DLLの関数を呼び出す（仮の例）
        # 実際のDLL仕様に合わせて修正必要
        try:
            # シリアル番号取得（例）
            serial_buffer = ctypes.create_string_buffer(50)
            result = self.dll.GetSerialNumber(serial_buffer)

            if result == 0:  # 成功
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

# テスト実行
if __name__ == "__main__":
    controller = TC-200Controller()
    info = controller.get_terminal_info()
    print(json.dumps(info, indent=2, ensure_ascii=False))
```

### Day 3-4: TMSサーバーとの通信

**エージェントのメイン処理**

```python
# agent/main.py
import time
import requests
import json
from terminal_controller import TC-200Controller

class TMSAgent:
    def __init__(self):
        self.controller = TC-200Controller()
        self.tms_url = "http://localhost:8000/api"  # 最初はローカルでテスト
        self.interval = 60  # 60秒ごとに送信

    def send_heartbeat(self):
        """TMSサーバーに状態を送信"""
        terminal_info = self.controller.get_terminal_info()

        try:
            response = requests.post(
                f"{self.tms_url}/heartbeat",
                json=terminal_info,
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ 送信成功: {terminal_info['serial_number']}")
                # サーバーからの指示を処理
                commands = response.json().get('commands', [])
                self.process_commands(commands)
            else:
                print(f"❌ 送信失敗: {response.status_code}")

        except Exception as e:
            print(f"❌ 通信エラー: {e}")

    def process_commands(self, commands):
        """サーバーからの指示を実行"""
        for cmd in commands:
            if cmd['type'] == 'reboot':
                print("🔄 再起動指示を受信")
                # 端末再起動のDLL呼び出し
            elif cmd['type'] == 'update_config':
                print("⚙️ 設定更新指示を受信")
                # 設定更新処理

    def run(self):
        """メインループ"""
        print("🚀 TMSエージェント起動")
        while True:
            self.send_heartbeat()
            time.sleep(self.interval)

# 実行
if __name__ == "__main__":
    agent = TMSAgent()
    agent.run()
```

### Day 5: Windows サービス化

**Windowsで自動起動させる**

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
        # ここでエージェントを起動
        from main import TMSAgent
        agent = TMSAgent()
        agent.run()

if __name__ == '__main__':
    # サービスとしてインストール
    # python install_service.py install
    # python install_service.py start
    win32serviceutil.HandleCommandLine(TMSAgentService)
```

---

## 🌐 Week 2: TMSサーバー構築（Django編）

### Day 6-7: Django プロジェクト作成

**1. プロジェクト初期化**

```bash
# コマンドプロンプトで実行
pip install django djangorestframework
django-admin startproject tms_server
cd tms_server
python manage.py startapp terminals
```

**2. モデル定義**

```python
# terminals/models.py
from django.db import models

class Terminal(models.Model):
    """端末マスター"""
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='シリアル番号'
    )
    store_name = models.CharField(
        max_length=100,
        verbose_name='店舗名',
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('online', 'オンライン'),
            ('offline', 'オフライン'),
            ('error', 'エラー'),
        ],
        default='offline',
        verbose_name='状態'
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最終通信時刻'
    )
    agent_version = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='エージェントバージョン'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登録日時'
    )

    class Meta:
        verbose_name = '端末'
        verbose_name_plural = '端末一覧'
        ordering = ['-last_heartbeat']

    def __str__(self):
        return f'{self.serial_number} ({self.store_name})'

class TerminalLog(models.Model):
    """通信ログ"""
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    log_type = models.CharField(max_length=20)  # heartbeat, error, command
    message = models.TextField()

    class Meta:
        verbose_name = 'ログ'
        verbose_name_plural = 'ログ一覧'
        ordering = ['-timestamp']
```

### Day 8-9: API エンドポイント作成

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
    """エージェントからのハートビート受信"""

    serial_number = request.data.get('serial_number')
    terminal_status = request.data.get('status', 'unknown')

    if not serial_number:
        return Response(
            {'error': 'シリアル番号が必要です'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 端末を取得または作成
    terminal, created = Terminal.objects.get_or_create(
        serial_number=serial_number
    )

    # 状態を更新
    terminal.status = terminal_status
    terminal.last_heartbeat = timezone.now()
    terminal.save()

    # ログを記録
    TerminalLog.objects.create(
        terminal=terminal,
        log_type='heartbeat',
        message=f'Status: {terminal_status}'
    )

    # レスポンス（端末への指示）
    commands = []

    # もし設定更新が必要なら
    if terminal.needs_update:  # このフィールドは後で追加
        commands.append({
            'type': 'update_config',
            'data': {'param1': 'value1'}
        })

    return Response({
        'status': 'ok',
        'commands': commands
    })

def dashboard(request):
    """管理画面のダッシュボード"""
    terminals = Terminal.objects.all()

    # 統計情報を計算
    stats = {
        'total': terminals.count(),
        'online': terminals.filter(status='online').count(),
        'offline': terminals.filter(status='offline').count(),
        'error': terminals.filter(status='error').count(),
    }

    # 最近のログ
    recent_logs = TerminalLog.objects.all()[:20]

    return render(request, 'dashboard.html', {
        'stats': stats,
        'terminals': terminals[:10],  # 最新10件
        'logs': recent_logs
    })
```

### Day 10: 管理画面作成

```html
<!-- templates/dashboard.html -->
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>TMS ダッシュボード</title>
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
    <meta http-equiv="refresh" content="30"> <!-- 30秒ごとに自動更新 -->
</head>
<body>
    <h1>🖥️ TMS ダッシュボード</h1>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-label">総端末数</div>
            <div class="stat-number">{{ stats.total }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">オンライン</div>
            <div class="stat-number online">{{ stats.online }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">オフライン</div>
            <div class="stat-number offline">{{ stats.offline }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">エラー</div>
            <div class="stat-number error">{{ stats.error }}</div>
        </div>
    </div>

    <h2>端末一覧</h2>
    <table>
        <thead>
            <tr>
                <th>シリアル番号</th>
                <th>店舗名</th>
                <th>状態</th>
                <th>最終通信</th>
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

    <h2>最近のログ</h2>
    <table>
        <thead>
            <tr>
                <th>時刻</th>
                <th>端末</th>
                <th>タイプ</th>
                <th>メッセージ</th>
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

## 🚀 Week 3-4: 実用化

### 必須機能の追加

1. **ファームウェア更新**
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

2. **アラート機能**
```python
def check_offline_terminals():
    """オフライン端末をチェック（定期実行）"""
    from datetime import timedelta
    threshold = timezone.now() - timedelta(minutes=5)

    offline_terminals = Terminal.objects.filter(
        last_heartbeat__lt=threshold,
        status='online'
    )

    for terminal in offline_terminals:
        terminal.status = 'offline'
        terminal.save()
        # メール送信
        send_alert_email(terminal)
```

3. **セキュリティ強化**
```python
# settings.py
ALLOWED_HOSTS = ['your-domain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# エージェント認証
class AgentToken(models.Model):
    terminal = models.OneToOneField(Terminal, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 📦 本番環境へのデプロイ

### AWS Lightsail（最も簡単な方法）

```bash
# 1. Lightsailインスタンス作成（月額$5〜）
# 2. SSHでログイン
# 3. 環境構築
sudo apt update
sudo apt install python3-pip nginx postgresql

# 4. Djangoアプリをアップロード
git clone your-repo
pip install -r requirements.txt

# 5. Gunicorn起動
gunicorn tms_server.wsgi:application

# 6. Nginx設定
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

---

## 💡 すぐできる次のアクション

### 今日中にやること

1. **フォルダ構成を作る**
```
Terminal Management System/
├── agent/              # エージェント（店舗PC）
│   ├── main.py
│   ├── terminal_controller.py
│   └── requirements.txt
├── server/             # TMSサーバー
│   ├── manage.py
│   ├── tms_server/
│   └── terminals/
└── docs/              # ドキュメント（既に作成済み）
```

2. **最初のテスト**
```python
# test_dll.py - DLLが読み込めるか確認
import ctypes

try:
    dll = ctypes.CDLL("TC-200.dll")
    print("✅ DLL読み込み成功！")
except Exception as e:
    print(f"❌ エラー: {e}")
    print("DLLファイルのパスを確認してください")
```

3. **Django起動確認**
```bash
django-admin startproject test_tms
cd test_tms
python manage.py runserver
# ブラウザで http://127.0.0.1:8000 を開く
```

---

## 🆘 困ったときの解決法

### よくあるエラーと対処

| エラー | 原因 | 解決法 |
|--------|------|--------|
| DLL読み込みエラー | パスが違う | 絶対パスで指定 |
| Django起動しない | ポート使用中 | 別ポート指定: runserver 8001 |
| 通信できない | ファイアウォール | Windows Defenderで許可 |
| データベースエラー | マイグレーション未実行 | python manage.py migrate |

### 質問テンプレート

エラーが出たら、以下の情報を教えてください：
1. 何をしようとしたか
2. 実行したコマンド
3. エラーメッセージ全文
4. 試したこと

---

## 📚 1週間の学習計画

| 日 | 学習内容 | 成果物 |
|----|---------|--------|
| 月 | Python基礎復習 | DLL呼び出しテスト |
| 火 | Django Tutorial Part1-2 | プロジェクト作成 |
| 水 | Django Tutorial Part3-4 | モデル作成 |
| 木 | エージェント作成 | 通信テスト |
| 金 | API作成 | heartbeatエンドポイント |
| 土 | 画面作成 | ダッシュボード表示 |
| 日 | 統合テスト | エージェント→サーバー連携 |

---

最初は完璧を求めず、「動くもの」を作ることが大切です。
1つずつ機能を追加していけば、必ず完成します！

質問があれば、具体的なコードと一緒にお答えします。