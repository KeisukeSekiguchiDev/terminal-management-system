from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from terminals.models import Customer, Terminal, TMSUser
import json


class HeartbeatAPITest(APITestCase):
    """Heartbeat API test"""
    
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="Shibuya Store"
        )
        self.url = reverse('agent_heartbeat')
    
    def test_heartbeat_success(self):
        """Normal heartbeat transmission"""
        data = {
            "serial_number": "TC-200-TEST001",
            "status": "online",
            "timestamp": "2025-11-24T12:00:00Z",
            "metrics": {
                "cpu_usage": 45,
                "memory_usage": 60,
                "disk_usage": 30,
                "temperature": 45
            },
            "firmware_version": "1.0.0",
            "agent_version": "1.0.0",
            "ip_address": "192.168.1.100"
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.terminal.refresh_from_db()
        self.assertEqual(self.terminal.status, "online")
        self.assertEqual(self.terminal.cpu_usage, 45)
    
    def test_heartbeat_invalid_serial(self):
        """Invalid serial number"""
        data = {
            "serial_number": "INVALID-001",
            "status": "online",
            "timestamp": "2025-11-24T12:00:00Z"
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
            "status": "online"
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TerminalAPITest(APITestCase):
    """Terminal API test"""
    
    def setUp(self):
        self.user = TMSUser.objects.create_user(
            username="testuser",
            password="testpass123",
            role="admin"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.customer = Customer.objects.create(
            company_name="Test Corporation",
            contact_email="test@example.com"
        )
        self.terminal = Terminal.objects.create(
            serial_number="TC-200-TEST001",
            customer=self.customer,
            store_name="Shibuya Store"
        )
    
    def test_terminal_list(self):
        """Terminal list API test"""
        url = reverse('terminal-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_terminal_detail(self):
        """Terminal detail API test"""
        url = reverse('terminal-detail', args=[self.terminal.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['serial_number'], "TC-200-TEST001")
    
    def test_terminal_update(self):
        """Terminal update API test"""
        url = reverse('terminal-detail', args=[self.terminal.id])
        data = {
            "store_name": "Updated Store Name"
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.terminal.refresh_from_db()
        self.assertEqual(self.terminal.store_name, "Updated Store Name")


class AuthenticationAPITest(APITestCase):
    """Authentication API test"""
    
    def setUp(self):
        self.user = TMSUser.objects.create_user(
            username="testuser",
            password="testpass123",
            role="operator"
        )
        self.client = APIClient()
    
    def test_login_success(self):
        """Login success test"""
        url = reverse('login')
        data = {
            "username": "testuser",
            "password": "testpass123"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
    
    def test_login_invalid_credentials(self):
        """Login with invalid credentials"""
        url = reverse('login')
        data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
