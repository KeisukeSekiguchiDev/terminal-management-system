from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta
from terminals.models import Customer, Terminal, Alert, FirmwareVersion, TMSUser


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
        customer_id = self.customer.id
        self.customer.delete()
        self.assertEqual(Terminal.objects.filter(customer_id=customer_id).count(), 0)


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
        with self.assertRaises(IntegrityError):
            Terminal.objects.create(
                serial_number="TC-200-TEST001",
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
            severity="critical",
            title="Terminal Offline",
            message="Terminal has gone offline"
        )
        self.assertEqual(alert.severity, "critical")
        self.assertFalse(alert.is_resolved)
        self.assertIsNotNone(alert.created_at)
    
    def test_alert_resolution(self):
        """Alert resolution test"""
        alert = Alert.objects.create(
            terminal=self.terminal,
            severity="critical",
            title="Terminal Offline",
            message="Terminal has gone offline"
        )
        
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        
        resolved_alert = Alert.objects.get(id=alert.id)
        self.assertTrue(resolved_alert.is_resolved)
        self.assertIsNotNone(resolved_alert.resolved_at)


class TMSUserModelTest(TestCase):
    """TMSUser model test"""
    
    def test_user_creation(self):
        """User creation test"""
        user = TMSUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role="operator"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.role, "operator")
        self.assertFalse(user.mfa_enabled)
    
    def test_user_role_choices(self):
        """Role choices test"""
        user = TMSUser.objects.create_user(
            username="admin",
            password="admin123",
            role="admin"
        )
        self.assertEqual(user.role, "admin")
