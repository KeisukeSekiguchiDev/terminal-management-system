# Test Specification
## Terminal Management System (TMS)

**Document Version**: 1.0
**Created Date**: November 24, 2025
**Target System**: TechCore Solutions TMS

---

## 1. Test Overview

### 1.1 Test Objectives
- Verify that the system operates according to requirements specification
- Early detection and correction of bugs
- Guarantee stable operation at 10,000 terminal scale

### 1.2 Test Scope

| Test Type | Target | Timing |
|-----------|--------|--------|
| Unit Test | Individual modules/functions | During coding |
| Integration Test | API/DB integration | After feature implementation |
| System Test | All features | After development completion |
| Load Test | Performance | Before release |
| Acceptance Test | Business flow | After production environment preparation |

---

## 2. Unit Test Specification

### 2.1 Django Models Test

```python
# tests/test_models.py

from django.test import TestCase
from django.utils import timezone
from terminals.models import Customer, Terminal, Alert

class CustomerModelTest(TestCase):
    """Customer model test"""

    def setUp(self):
        """Test data preparation"""
        self.customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_person="Taro Yamada",
            contact_email="yamada@test.com",
            contact_phone="03-1234-5678",
            contract_type="standard"
        )

    def test_customer_creation(self):
        """Customer creation test"""
        self.assertEqual(self.customer.company_name, "Test Corporation")
        self.assertEqual(self.customer.contract_type, "standard")
        self.assertTrue(self.customer.created_at)

    def test_customer_string_representation(self):
        """String representation test"""
        self.assertEqual(str(self.customer), "Test Corporation")

    def test_customer_deletion_cascades_to_terminals(self):
        """Cascade deletion test"""
        terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="Test Store"
        )
        self.customer.delete()
        self.assertEqual(Terminal.objects.filter(serial_number="TC-200-TEST001").count(), 0)


class TerminalModelTest(TestCase):
    """Terminal model test"""

    def setUp(self):
        self.customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="Shibuya Store",
            status="online"
        )

    def test_terminal_creation(self):
        """Terminal creation test"""
        self.assertEqual(self.terminal.serial_number, "TC-200-TEST001")
        self.assertEqual(self.terminal.status, "online")
        self.assertEqual(self.terminal.firmware_version, "1.0.0")

    def test_terminal_unique_serial_number(self):
        """Serial number uniqueness test"""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Terminal.objects.create(
                serial_number="TC-200-TEST001",  # Duplicate
                customer=self.customer,
                store_name="Shinjuku Store"
            )

    def test_terminal_status_update(self):
        """Status update test"""
        self.terminal.status = "offline"
        self.terminal.last_heartbeat = timezone.now()
        self.terminal.save()

        updated_terminal = Terminal.objects.get(id=self.terminal.id)
        self.assertEqual(updated_terminal.status, "offline")
        self.assertIsNotNone(updated_terminal.last_heartbeat)


class AlertModelTest(TestCase):
    """Alert model test"""

    def setUp(self):
        self.customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="Shibuya Store"
        )

    def test_alert_creation(self):
        """Alert creation test"""
        alert = Alert.objects.create(
            terminal=self.terminal,
            alert_type="offline",
            message="Terminal has gone offline"
        )
        self.assertEqual(alert.alert_type, "offline")
        self.assertFalse(alert.is_resolved)
        self.assertIsNotNone(alert.created_at)

    def test_alert_resolution(self):
        """Alert resolution test"""
        alert = Alert.objects.create(
            terminal=self.terminal,
            alert_type="offline",
            message="Terminal has gone offline"
        )

        # Resolve alert
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = "Taro Tanaka"
        alert.save()

        resolved_alert = Alert.objects.get(id=alert.id)
        self.assertTrue(resolved_alert.is_resolved)
        self.assertIsNotNone(resolved_alert.resolved_at)
        self.assertEqual(resolved_alert.resolved_by, "Taro Tanaka")
```

### 2.2 Views/API Test

```python
# tests/test_views.py

from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from terminals.models import Customer, Terminal
import json

class HeartbeatAPITest(APITestCase):
    """Heartbeat API test"""

    def setUp(self):
        self.customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="Shibuya Store"
        )
        self.url = reverse('api:heartbeat')

    def test_heartbeat_success(self):
        """Normal heartbeat transmission"""
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

        # DB update confirmation
        terminal = Terminal.objects.get(serial_number="TC-200-TEST001")
        self.assertEqual(terminal.status, "online")
        self.assertEqual(terminal.cpu_usage, 45)

    def test_heartbeat_invalid_serial(self):
        """Invalid serial number"""
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
        """Missing required fields"""
        data = {
            "status": "online"  # serial_number is missing
        }

        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TerminalListViewTest(TestCase):
    """Terminal list view test"""

    def setUp(self):
        self.client = Client()
        self.url = reverse('terminals:list')

        # Create test data
        customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_email="test@example.com"
        )

        for i in range(15):  # For pagination test
            Terminal.objects.create(
                serial_number=f"TC-200-TEST{i:03d}",
                customer=customer,
                store_name=f"Store {i}",
                status="online" if i % 2 == 0 else "offline"
            )

    def test_terminal_list_access(self):
        """List view access test"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Terminal List")

    def test_terminal_list_pagination(self):
        """Pagination test"""
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['terminals']), 10)  # 10 per page

    def test_terminal_list_filter(self):
        """Filtering test"""
        response = self.client.get(self.url, {'status': 'online'})
        for terminal in response.context['terminals']:
            self.assertEqual(terminal.status, 'online')
```

---

## 3. Integration Test Specification

### 3.1 Agent-Server Integration Test

```python
# tests/test_integration.py

import time
import threading
from django.test import TestCase
from agent.main import TMSAgent
from terminals.models import Terminal

class AgentServerIntegrationTest(TestCase):
    """Agent-server integration test"""

    def test_agent_heartbeat_integration(self):
        """Agent heartbeat transmission integration test"""

        # Create test terminal
        terminal = Terminal.objects.create(
            serial_number="TC-200-INT001",
            customer_id=1,
            store_name="Integration Test Store"
        )

        # Start agent
        agent = TMSAgent(
            serial_number="TC-200-INT001",
            server_url="http://localhost:8000",
            interval=5  # 5 second interval
        )

        # Run agent in background
        agent_thread = threading.Thread(target=agent.start)
        agent_thread.daemon = True
        agent_thread.start()

        # Wait 10 seconds
        time.sleep(10)

        # Verify heartbeat was updated
        terminal.refresh_from_db()
        self.assertEqual(terminal.status, "online")
        self.assertIsNotNone(terminal.last_heartbeat)

        # Stop agent
        agent.stop()
```

### 3.2 Alert Integration Test

```python
def test_offline_alert_generation(self):
    """Offline alert generation test"""

    # Set terminal to online
    terminal = Terminal.objects.create(
        serial_number="TC-200-ALERT001",
        customer_id=1,
        store_name="Alert Test Store",
        status="online",
        last_heartbeat=timezone.now()
    )

    # Simulate 10 minutes elapsed
    terminal.last_heartbeat = timezone.now() - timedelta(minutes=10)
    terminal.save()

    # Execute monitoring task
    from terminals.tasks import check_offline_terminals
    check_offline_terminals()

    # Verify alert was generated
    alerts = Alert.objects.filter(
        terminal=terminal,
        alert_type="offline"
    )
    self.assertEqual(alerts.count(), 1)
```

---

## 4. Load Test Specification

### 4.1 Performance Test

```python
# tests/test_performance.py

import concurrent.futures
import time
from django.test import TestCase
from terminals.models import Terminal

class PerformanceTest(TestCase):
    """Performance test"""

    def test_concurrent_heartbeats(self):
        """Concurrent heartbeat processing test"""

        # Create 1000 terminals
        terminals = []
        for i in range(1000):
            terminal = Terminal.objects.create(
                serial_number=f"TC-200-PERF{i:04d}",
                customer_id=1,
                store_name=f"Load Test Store {i}"
            )
            terminals.append(terminal)

        # Send 100 heartbeats concurrently
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

            # Verify results
            for future in concurrent.futures.as_completed(futures):
                self.assertEqual(future.result(), 200)

        elapsed_time = time.time() - start_time

        # Complete within 3 seconds
        self.assertLess(elapsed_time, 3.0)
```

### 4.2 Database Load Test

```python
def test_database_query_performance(self):
    """Database query performance test"""

    # Create 10000 test data records
    terminals = []
    for i in range(10000):
        terminals.append(Terminal(
            serial_number=f"TC-200-DB{i:05d}",
            customer_id=(i % 100) + 1,  # Distribute across 100 companies
            store_name=f"Store {i}",
            status="online" if i % 3 == 0 else "offline"
        ))
    Terminal.objects.bulk_create(terminals)

    # Measure query performance
    start_time = time.time()

    # Aggregate by customer
    from django.db.models import Count
    result = Terminal.objects.values('customer_id').annotate(
        total=Count('id')
    )
    list(result)  # Execute query

    elapsed_time = time.time() - start_time

    # Complete within 1 second
    self.assertLess(elapsed_time, 1.0)
```

---

## 5. System Test Scenarios

### 5.1 E2E Test from Terminal Registration to Monitoring

| Step | Action | Expected Result | Verification Method |
|------|--------|-----------------|---------------------|
| 1 | Register new customer from admin panel | Customer is registered | DB check |
| 2 | Associate terminal with customer | Terminal is added under customer | List display |
| 3 | Send heartbeat from agent | Status becomes online | Screen check |
| 4 | Stop agent | Alert generated after 10 minutes | Alert screen |
| 5 | Record alert response | Alert marked as resolved | Status check |

### 5.2 Firmware Update Scenario

```python
# tests/test_scenarios.py

class FirmwareUpdateScenarioTest(TestCase):
    """Firmware update scenario test"""

    def test_firmware_update_flow(self):
        """Firmware update flow complete test"""

        # 1. Create update task
        update_task = UpdateTask.objects.create(
            name="v2.0.0 Update",
            firmware_version="2.0.0",
            target_terminals="all"
        )

        # 2. Select target terminals
        terminals = Terminal.objects.filter(
            firmware_version__lt="2.0.0"
        )
        update_task.terminals.set(terminals)

        # 3. Execute update
        update_task.execute()

        # 4. Check progress
        self.assertEqual(
            update_task.status,
            "in_progress"
        )

        # 5. Confirm completion (simulate)
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

## 6. Test Execution Methods

### 6.1 Running Tests in Development Environment

```bash
# Run all tests
python manage.py test

# Test specific app
python manage.py test terminals

# Run specific test class
python manage.py test terminals.tests.test_models.CustomerModelTest

# Coverage measurement
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### 6.2 CI/CD Pipeline Configuration

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

## 7. Test Data

### 7.1 Master Data

```python
# fixtures/test_data.json
{
  "model": "terminals.customer",
  "pk": 1,
  "fields": {
    "company_name": "ABC Mart",
    "contact_person": "Ichiro Suzuki",
    "contact_email": "suzuki@abc-mart.com",
    "contact_phone": "03-1111-2222",
    "contract_type": "premium"
  }
}
```

### 7.2 Test Data Generation Script

```python
# scripts/generate_test_data.py

import random
from faker import Faker
from terminals.models import Customer, Terminal

fake = Faker('ja_JP')

def generate_test_data():
    """Generate test data"""

    # Create 100 customers
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

    # Assign 10-100 terminals to each customer
    for customer in customers:
        terminal_count = random.randint(10, 100)
        for j in range(terminal_count):
            Terminal.objects.create(
                serial_number=f"TC-200-{customer.id:03d}{j:04d}",
                customer=customer,
                store_name=f"{fake.city()} Store #{j}",
                status=random.choice(['online', 'offline', 'error']),
                firmware_version=random.choice(['1.0.0', '1.1.0', '2.0.0'])
            )

    print(f"Creation complete: {len(customers)} companies, {Terminal.objects.count()} terminals")

if __name__ == "__main__":
    generate_test_data()
```

---

## 8. Acceptance Test Checklist

### 8.1 Functional Requirements Check

- [ ] **Terminal Management**
  - [ ] Terminal list display works correctly
  - [ ] Filtering function works
  - [ ] Pagination works
  - [ ] Terminal detail screen displays

- [ ] **Monitoring Function**
  - [ ] Heartbeat is received correctly
  - [ ] Offline detection works within 10 minutes
  - [ ] CPU/memory usage is recorded

- [ ] **Alert Function**
  - [ ] Alerts are automatically generated
  - [ ] Email notifications are sent
  - [ ] Alert resolution is recorded

- [ ] **Firmware Update**
  - [ ] Update tasks can be created
  - [ ] Target terminals are correctly selected
  - [ ] Update progress can be monitored

### 8.2 Non-functional Requirements Check

- [ ] **Performance**
  - [ ] Management of 10,000 terminals is possible
  - [ ] Screen response within 3 seconds
  - [ ] Support for 100 simultaneous connections

- [ ] **Security**
  - [ ] Login authentication works
  - [ ] Permission control is applied
  - [ ] Communication via HTTPS

- [ ] **Availability**
  - [ ] 24-hour continuous operation possible
  - [ ] Automatic recovery on error
  - [ ] Data backup works

---

## 9. Troubleshooting

### 9.1 Common Test Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Database connection error | DB not running | Verify PostgreSQL is running |
| Permission denied | Insufficient permissions | Check test user permissions |
| Timeout error | Processing delay | Adjust timeout value |
| Import error | Missing module | Check requirements.txt |

### 9.2 Debugging Methods

```python
# Debugging during tests
import pdb

def test_complex_logic(self):
    # Set breakpoint
    pdb.set_trace()

    # Code to debug
    result = complex_function()

    # Assertion
    self.assertEqual(result, expected_value)
```

---

## Summary

Following this test specification:
1. **Create unit tests in parallel with development**
2. **Perform integration tests after feature completion**
3. **Confirm performance with load tests before release**
4. **Confirm requirement fulfillment with acceptance tests**

Test coverage target: **80% or higher**
