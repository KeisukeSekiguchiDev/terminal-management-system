# テスト仕様書
## Terminal Management System (TMS)

**文書バージョン**: 1.0
**作成日**: 2025年11月24日
**対象システム**: TechCore Solutions TMS

---

## 1. テスト概要

### 1.1 テスト目的
- システムが要件定義通りに動作することを確認
- バグの早期発見と修正
- 10,000台規模での安定稼働を保証

### 1.2 テスト範囲

| テスト種別 | 対象 | 実施タイミング |
|-----------|------|---------------|
| 単体テスト | 各モジュール・関数 | コーディング時 |
| 結合テスト | API・DB連携 | 機能実装完了後 |
| システムテスト | 全機能 | 開発完了後 |
| 負荷テスト | パフォーマンス | リリース前 |
| 受入テスト | 業務フロー | 本番環境準備後 |

---

## 2. 単体テスト仕様

### 2.1 Django Models テスト

```python
# tests/test_models.py

from django.test import TestCase
from django.utils import timezone
from terminals.models import Customer, Terminal, Alert

class CustomerModelTest(TestCase):
    """顧客モデルのテスト"""

    def setUp(self):
        """テストデータ準備"""
        self.customer = Customer.objects.create(
            company_name="テスト商事",
            contact_person="山田太郎",
            contact_email="yamada@test.com",
            contact_phone="03-1234-5678",
            contract_type="standard"
        )

    def test_customer_creation(self):
        """顧客作成テスト"""
        self.assertEqual(self.customer.company_name, "テスト商事")
        self.assertEqual(self.customer.contract_type, "standard")
        self.assertTrue(self.customer.created_at)

    def test_customer_string_representation(self):
        """文字列表現テスト"""
        self.assertEqual(str(self.customer), "テスト商事")

    def test_customer_deletion_cascades_to_terminals(self):
        """カスケード削除テスト"""
        terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="テスト店舗"
        )
        self.customer.delete()
        self.assertEqual(Terminal.objects.filter(serial_number="TC-200-TEST001").count(), 0)


class TerminalModelTest(TestCase):
    """端末モデルのテスト"""

    def setUp(self):
        self.customer = Customer.objects.create(
            company_name="テスト商事",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="渋谷店",
            status="online"
        )

    def test_terminal_creation(self):
        """端末作成テスト"""
        self.assertEqual(self.terminal.serial_number, "TC-200-TEST001")
        self.assertEqual(self.terminal.status, "online")
        self.assertEqual(self.terminal.firmware_version, "1.0.0")

    def test_terminal_unique_serial_number(self):
        """シリアル番号一意性テスト"""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Terminal.objects.create(
                serial_number="TC-200-TEST001",  # 重複
                customer=self.customer,
                store_name="新宿店"
            )

    def test_terminal_status_update(self):
        """ステータス更新テスト"""
        self.terminal.status = "offline"
        self.terminal.last_heartbeat = timezone.now()
        self.terminal.save()

        updated_terminal = Terminal.objects.get(id=self.terminal.id)
        self.assertEqual(updated_terminal.status, "offline")
        self.assertIsNotNone(updated_terminal.last_heartbeat)


class AlertModelTest(TestCase):
    """アラートモデルのテスト"""

    def setUp(self):
        self.customer = Customer.objects.create(
            company_name="テスト商事",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="渋谷店"
        )

    def test_alert_creation(self):
        """アラート作成テスト"""
        alert = Alert.objects.create(
            terminal=self.terminal,
            alert_type="offline",
            message="端末がオフラインになりました"
        )
        self.assertEqual(alert.alert_type, "offline")
        self.assertFalse(alert.is_resolved)
        self.assertIsNotNone(alert.created_at)

    def test_alert_resolution(self):
        """アラート解決テスト"""
        alert = Alert.objects.create(
            terminal=self.terminal,
            alert_type="offline",
            message="端末がオフラインになりました"
        )

        # アラート解決
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = "田中太郎"
        alert.save()

        resolved_alert = Alert.objects.get(id=alert.id)
        self.assertTrue(resolved_alert.is_resolved)
        self.assertIsNotNone(resolved_alert.resolved_at)
        self.assertEqual(resolved_alert.resolved_by, "田中太郎")
```

### 2.2 Views/API テスト

```python
# tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from terminals.models import Customer, Terminal
import json

class HeartbeatAPITest(APITestCase):
    """ハートビートAPIのテスト"""

    def setUp(self):
        self.customer = Customer.objects.create(
            company_name="テスト商事",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="渋谷店"
        )
        self.url = reverse('api:heartbeat')

    def test_heartbeat_success(self):
        """正常なハートビート送信"""
        data = {
            "serial_number": "TC-200-TEST001",
            "status": "online",
            "metrics": {
                "cpu_usage": 45,
                "memory_usage": 60,
                "disk_usage": 30
            }
        }

        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')

        # DB更新確認
        terminal = Terminal.objects.get(serial_number="TC-200-TEST001")
        self.assertEqual(terminal.status, "online")
        self.assertEqual(terminal.cpu_usage, 45)

    def test_heartbeat_invalid_serial(self):
        """無効なシリアル番号"""
        data = {
            "serial_number": "INVALID-001",
            "status": "online"
        }

        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_heartbeat_missing_fields(self):
        """必須フィールド欠落"""
        data = {
            "status": "online"  # serial_numberが欠落
        }

        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TerminalListViewTest(TestCase):
    """端末一覧画面のテスト"""

    def setUp(self):
        self.client = Client()
        self.url = reverse('terminals:list')

        # テストデータ作成
        customer = Customer.objects.create(
            company_name="テスト商事",
            contact_email="test@example.com"
        )

        for i in range(15):  # ページネーションテスト用
            Terminal.objects.create(
                serial_number=f"TC-200-TEST{i:03d}",
                customer=customer,
                store_name=f"店舗{i}",
                status="online" if i % 2 == 0 else "offline"
            )

    def test_terminal_list_access(self):
        """一覧画面アクセステスト"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "端末一覧")

    def test_terminal_list_pagination(self):
        """ページネーションテスト"""
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['terminals']), 10)  # 1ページ10件

    def test_terminal_list_filter(self):
        """フィルタリングテスト"""
        response = self.client.get(self.url, {'status': 'online'})
        for terminal in response.context['terminals']:
            self.assertEqual(terminal.status, 'online')
```

---

## 3. 結合テスト仕様

### 3.1 エージェント・サーバー連携テスト

```python
# tests/test_integration.py

import time
import threading
from django.test import TestCase
from agent.main import TMSAgent
from terminals.models import Terminal

class AgentServerIntegrationTest(TestCase):
    """エージェント・サーバー連携テスト"""

    def test_agent_heartbeat_integration(self):
        """エージェントのハートビート送信統合テスト"""

        # テスト用端末作成
        terminal = Terminal.objects.create(
            serial_number="TC-200-INT001",
            customer_id=1,
            store_name="統合テスト店舗"
        )

        # エージェント起動
        agent = TMSAgent(
            serial_number="TC-200-INT001",
            server_url="http://localhost:8000",
            interval=5  # 5秒間隔
        )

        # バックグラウンドでエージェント実行
        agent_thread = threading.Thread(target=agent.start)
        agent_thread.daemon = True
        agent_thread.start()

        # 10秒待機
        time.sleep(10)

        # ハートビートが更新されているか確認
        terminal.refresh_from_db()
        self.assertEqual(terminal.status, "online")
        self.assertIsNotNone(terminal.last_heartbeat)

        # エージェント停止
        agent.stop()
```

### 3.2 アラート連携テスト

```python
def test_offline_alert_generation(self):
    """オフラインアラート生成テスト"""

    # 端末をオンラインに設定
    terminal = Terminal.objects.create(
        serial_number="TC-200-ALERT001",
        customer_id=1,
        store_name="アラートテスト店舗",
        status="online",
        last_heartbeat=timezone.now()
    )

    # 10分経過をシミュレート
    terminal.last_heartbeat = timezone.now() - timedelta(minutes=10)
    terminal.save()

    # モニタリングタスク実行
    from terminals.tasks import check_offline_terminals
    check_offline_terminals()

    # アラートが生成されたか確認
    alerts = Alert.objects.filter(
        terminal=terminal,
        alert_type="offline"
    )
    self.assertEqual(alerts.count(), 1)
```

---

## 4. 負荷テスト仕様

### 4.1 パフォーマンステスト

```python
# tests/test_performance.py

import concurrent.futures
import time
from django.test import TestCase
from terminals.models import Terminal

class PerformanceTest(TestCase):
    """パフォーマンステスト"""

    def test_concurrent_heartbeats(self):
        """同時ハートビート処理テスト"""

        # 1000端末を作成
        terminals = []
        for i in range(1000):
            terminal = Terminal.objects.create(
                serial_number=f"TC-200-PERF{i:04d}",
                customer_id=1,
                store_name=f"負荷テスト店舗{i}"
            )
            terminals.append(terminal)

        # 同時に100件のハートビートを送信
        def send_heartbeat(serial_number):
            client = Client()
            response = client.post('/api/heartbeat', {
                'serial_number': serial_number,
                'status': 'online',
                'metrics': {'cpu_usage': 50}
            })
            return response.status_code

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for i in range(100):
                future = executor.submit(
                    send_heartbeat,
                    f"TC-200-PERF{i:04d}"
                )
                futures.append(future)

            # 結果確認
            for future in concurrent.futures.as_completed(futures):
                self.assertEqual(future.result(), 200)

        elapsed_time = time.time() - start_time

        # 3秒以内に処理完了
        self.assertLess(elapsed_time, 3.0)
```

### 4.2 データベース負荷テスト

```python
def test_database_query_performance(self):
    """データベースクエリ性能テスト"""

    # 10000件のテストデータ作成
    terminals = []
    for i in range(10000):
        terminals.append(Terminal(
            serial_number=f"TC-200-DB{i:05d}",
            customer_id=(i % 100) + 1,  # 100社に分散
            store_name=f"店舗{i}",
            status="online" if i % 3 == 0 else "offline"
        ))
    Terminal.objects.bulk_create(terminals)

    # クエリ性能測定
    start_time = time.time()

    # 顧客別集計
    from django.db.models import Count
    result = Terminal.objects.values('customer_id').annotate(
        total=Count('id')
    )
    list(result)  # クエリ実行

    elapsed_time = time.time() - start_time

    # 1秒以内に完了
    self.assertLess(elapsed_time, 1.0)
```

---

## 5. システムテストシナリオ

### 5.1 端末登録から監視までのE2Eテスト

| Step | アクション | 期待結果 | 確認方法 |
|------|-----------|---------|----------|
| 1 | 管理画面から新規顧客登録 | 顧客が登録される | DB確認 |
| 2 | 顧客に端末を紐付け | 端末が顧客配下に追加 | 一覧表示 |
| 3 | エージェントからハートビート送信 | ステータスがonlineに | 画面確認 |
| 4 | エージェントを停止 | 10分後にアラート発生 | アラート画面 |
| 5 | アラート対応を記録 | アラートが解決済みに | ステータス確認 |

### 5.2 ファームウェア更新シナリオ

```python
# tests/test_scenarios.py

class FirmwareUpdateScenarioTest(TestCase):
    """ファームウェア更新シナリオテスト"""

    def test_firmware_update_flow(self):
        """ファームウェア更新フロー全体テスト"""

        # 1. 更新タスク作成
        update_task = UpdateTask.objects.create(
            name="v2.0.0アップデート",
            firmware_version="2.0.0",
            target_terminals="all"
        )

        # 2. 対象端末選択
        terminals = Terminal.objects.filter(
            firmware_version__lt="2.0.0"
        )
        update_task.terminals.set(terminals)

        # 3. 更新実行
        update_task.execute()

        # 4. 進捗確認
        self.assertEqual(
            update_task.status,
            "in_progress"
        )

        # 5. 完了確認（シミュレート）
        for terminal in terminals:
            terminal.firmware_version = "2.0.0"
            terminal.save()

        update_task.check_completion()
        self.assertEqual(
            update_task.status,
            "completed"
        )
```

---

## 6. テスト実行方法

### 6.1 開発環境でのテスト実行

```bash
# 全テスト実行
python manage.py test

# 特定アプリのテスト
python manage.py test terminals

# 特定テストクラス実行
python manage.py test terminals.tests.test_models.CustomerModelTest

# カバレッジ測定
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # htmlレポート生成
```

### 6.2 CI/CDパイプライン設定

```yaml
# .github/workflows/test.yml

name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      env:
        DATABASE_URL: postgres://postgres:password@localhost/tms_test
      run: |
        python manage.py migrate
        python manage.py test

    - name: Generate coverage report
      run: |
        coverage run --source='.' manage.py test
        coverage xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## 7. テストデータ

### 7.1 マスターデータ

```python
# fixtures/test_data.json
{
  "model": "terminals.customer",
  "pk": 1,
  "fields": {
    "company_name": "ABCマート",
    "contact_person": "鈴木一郎",
    "contact_email": "suzuki@abc-mart.com",
    "contact_phone": "03-1111-2222",
    "contract_type": "premium"
  }
}
```

### 7.2 テストデータ生成スクリプト

```python
# scripts/generate_test_data.py

import random
from faker import Faker
from terminals.models import Customer, Terminal

fake = Faker('ja_JP')

def generate_test_data():
    """テストデータ生成"""

    # 100社の顧客作成
    customers = []
    for i in range(100):
        customer = Customer.objects.create(
            company_name=fake.company(),
            contact_person=fake.name(),
            contact_email=fake.email(),
            contact_phone=fake.phone_number(),
            contract_type=random.choice(['basic', 'standard', 'premium'])
        )
        customers.append(customer)

    # 各顧客に10-100台の端末を割り当て
    for customer in customers:
        terminal_count = random.randint(10, 100)
        for j in range(terminal_count):
            Terminal.objects.create(
                serial_number=f"TC-200-{customer.id:03d}{j:04d}",
                customer=customer,
                store_name=f"{fake.city()}{j}号店",
                status=random.choice(['online', 'offline', 'error']),
                firmware_version=random.choice(['1.0.0', '1.1.0', '2.0.0'])
            )

    print(f"作成完了: {len(customers)}社, {Terminal.objects.count()}台")

if __name__ == "__main__":
    generate_test_data()
```

---

## 8. 受入テストチェックリスト

### 8.1 機能要件チェック

- [ ] **端末管理**
  - [ ] 端末一覧表示が正常に動作
  - [ ] フィルタリング機能が動作
  - [ ] ページネーションが動作
  - [ ] 端末詳細画面が表示される

- [ ] **監視機能**
  - [ ] ハートビートが正常に受信される
  - [ ] オフライン検知が10分以内に動作
  - [ ] CPU/メモリ使用率が記録される

- [ ] **アラート機能**
  - [ ] アラートが自動生成される
  - [ ] メール通知が送信される
  - [ ] アラート解決が記録される

- [ ] **ファームウェア更新**
  - [ ] 更新タスクが作成できる
  - [ ] 対象端末が正しく選択される
  - [ ] 更新進捗が確認できる

### 8.2 非機能要件チェック

- [ ] **性能**
  - [ ] 10,000端末の管理が可能
  - [ ] 画面応答3秒以内
  - [ ] 同時100接続に対応

- [ ] **セキュリティ**
  - [ ] ログイン認証が動作
  - [ ] 権限制御が適用される
  - [ ] HTTPSで通信される

- [ ] **可用性**
  - [ ] 24時間連続稼働可能
  - [ ] エラー時の自動復旧
  - [ ] データバックアップ動作

---

## 9. トラブルシューティング

### 9.1 よくあるテストエラー

| エラー | 原因 | 対処法 |
|--------|------|--------|
| Database connection error | DB未起動 | PostgreSQL起動確認 |
| Permission denied | 権限不足 | テストユーザー権限確認 |
| Timeout error | 処理遅延 | タイムアウト値調整 |
| Import error | モジュール不足 | requirements.txt確認 |

### 9.2 デバッグ方法

```python
# テスト時のデバッグ
import pdb

def test_complex_logic(self):
    # ブレークポイント設定
    pdb.set_trace()

    # デバッグしたいコード
    result = complex_function()

    # アサーション
    self.assertEqual(result, expected_value)
```

---

## まとめ

このテスト仕様書に従って：
1. **開発と並行して単体テストを作成**
2. **機能完成後に結合テストを実施**
3. **リリース前に負荷テストで性能確認**
4. **受入テストで要件充足を確認**

テストカバレッジ目標: **80%以上**