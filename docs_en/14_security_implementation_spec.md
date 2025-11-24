# Security Implementation Specification
## Terminal Management System (TMS)

**Document Version**: 1.0
**Created Date**: November 24, 2025
**Security Level**: High (Financial terminal management)

---

## 1. Security Overview

### 1.1 Security Requirements

| Category | Requirement | Compliance Level |
|----------|-------------|------------------|
| Authentication | Multi-factor authentication (MFA) support | Required |
| Encryption | Encryption of communication and stored data | Required |
| Access Control | Role-based access control | Required |
| Audit | Logging of all operations | Required |
| PCI DSS | Level 3 compliance | Recommended |

### 1.2 Threat Model

```
Attacker -> [Internet] -> ALB -> EC2 -> RDS
   |                        |
   +-> [Store PC] -> Agent -> TC-200 Terminal

Main Threats:
1. Unauthorized access (intrusion into admin panel)
2. Data breach (customer information, terminal information)
3. Tampering (firmware, configuration)
4. DoS attack (service disruption)
5. Man-in-the-middle attack (communication interception)
```

---

## 2. Authentication and Authorization Implementation

### 2.1 User Authentication (Django)

```python
# server/authentication/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
import pyotp
import qrcode
from io import BytesIO
import base64

class TMSUser(AbstractUser):
    """Custom user model"""

    ROLE_CHOICES = [
        ('admin', 'System Administrator'),
        ('operator', 'Operations Operator'),
        ('support', 'Support Staff'),
        ('viewer', 'View Only'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name='Role'
    )

    # MFA settings
    mfa_enabled = models.BooleanField(
        default=False,
        verbose_name='MFA Enabled'
    )
    mfa_secret = models.CharField(
        max_length=32,
        blank=True,
        verbose_name='MFA Secret'
    )

    # Security settings
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Password Changed At'
    )
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name='Failed Login Attempts'
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Locked Until'
    )

    # Audit information
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Last Login IP'
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name='Created By'
    )

    class Meta:
        verbose_name = 'TMS User'
        verbose_name_plural = 'TMS Users'

    def generate_mfa_secret(self):
        """Generate MFA secret"""
        self.mfa_secret = pyotp.random_base32()
        self.save()
        return self.mfa_secret

    def get_mfa_qr_code(self):
        """Generate MFA QR code"""
        if not self.mfa_secret:
            self.generate_mfa_secret()

        provisioning_uri = pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email,
            issuer_name='TechCore TMS'
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    def verify_mfa_token(self, token):
        """Verify MFA token"""
        if not self.mfa_enabled or not self.mfa_secret:
            return True

        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)

    def is_locked(self):
        """Check account lock status"""
        from django.utils import timezone

        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def increment_failed_login(self):
        """Increment failed login count"""
        from django.utils import timezone
        from datetime import timedelta

        self.failed_login_attempts += 1

        # Lock for 30 minutes after 5 failures
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=30)

        self.save()

    def reset_failed_login(self):
        """Reset failed login count"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save()
```

### 2.2 Authentication View Implementation

```python
# server/authentication/views.py

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import TMSUser
from .decorators import require_role
import logging

logger = logging.getLogger(__name__)

@csrf_protect
def login_view(request):
    """Login view (MFA enabled)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        mfa_token = request.POST.get('mfa_token', '')

        # Get IP address
        ip_address = get_client_ip(request)

        try:
            user = TMSUser.objects.get(username=username)

            # Check account lock
            if user.is_locked():
                logger.warning(f"Access attempt to locked account: {username} from {ip_address}")
                messages.error(request, 'Account is locked. Please wait and try again later.')
                return render(request, 'authentication/login.html')

            # Authenticate
            user = authenticate(request, username=username, password=password)

            if user:
                # MFA verification
                if user.mfa_enabled:
                    if not user.verify_mfa_token(mfa_token):
                        user.increment_failed_login()
                        logger.warning(f"MFA authentication failed: {username} from {ip_address}")
                        messages.error(request, 'Authentication code is incorrect.')
                        return render(request, 'authentication/login.html')

                # Login success
                login(request, user)
                user.last_login_ip = ip_address
                user.reset_failed_login()
                user.save()

                # Session settings
                request.session.set_expiry(3600)  # 1 hour
                request.session['user_role'] = user.role

                # Audit log
                log_security_event(
                    event_type='login_success',
                    user=user,
                    ip_address=ip_address,
                    details={'username': username}
                )

                logger.info(f"Login success: {username} from {ip_address}")
                return redirect('dashboard')
            else:
                # Login failure
                if TMSUser.objects.filter(username=username).exists():
                    user = TMSUser.objects.get(username=username)
                    user.increment_failed_login()

                log_security_event(
                    event_type='login_failed',
                    user=None,
                    ip_address=ip_address,
                    details={'username': username}
                )

                logger.warning(f"Login failed: {username} from {ip_address}")
                messages.error(request, 'Username or password is incorrect.')

        except TMSUser.DoesNotExist:
            logger.warning(f"Login attempt for non-existent user: {username} from {ip_address}")
            messages.error(request, 'Username or password is incorrect.')

    return render(request, 'authentication/login.html')

@login_required
@csrf_protect
def logout_view(request):
    """Logout"""
    user = request.user
    ip_address = get_client_ip(request)

    # Audit log
    log_security_event(
        event_type='logout',
        user=user,
        ip_address=ip_address,
        details={}
    )

    logout(request)
    logger.info(f"Logout: {user.username} from {ip_address}")

    return redirect('login')

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 2.3 Role-Based Access Control

```python
# server/authentication/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def require_role(*allowed_roles):
    """Role required decorator"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if request.user.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

# Usage example
@login_required
@require_role('admin', 'operator')
def firmware_update_view(request):
    """Firmware update screen (admin and operator only)"""
    pass
```

### 2.4 API Authentication (For Agent)

```python
# server/api/authentication.py

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache
import hashlib
import hmac
import time

class AgentAuthentication(BaseAuthentication):
    """Agent authentication"""

    def authenticate(self, request):
        # Get API key header
        api_key = request.META.get('HTTP_X_API_KEY')
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')

        if not all([api_key, signature, timestamp]):
            return None

        # Timestamp verification (within 5 minutes)
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            raise AuthenticationFailed('Request has expired')

        # Search for agent
        try:
            from terminals.models import Terminal
            terminal = Terminal.objects.get(api_key=api_key)
        except Terminal.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')

        # Signature verification
        expected_signature = self.generate_signature(
            api_key=api_key,
            secret_key=terminal.secret_key,
            timestamp=timestamp,
            body=request.body.decode('utf-8')
        )

        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationFailed('Invalid signature')

        # Rate limit check
        if not self.check_rate_limit(api_key):
            raise AuthenticationFailed('Rate limit exceeded')

        return (terminal, None)

    def generate_signature(self, api_key, secret_key, timestamp, body):
        """Generate signature"""
        message = f"{api_key}:{timestamp}:{body}"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def check_rate_limit(self, api_key):
        """Rate limit check (60 requests per minute max)"""
        key = f"rate_limit:{api_key}"
        count = cache.get(key, 0)

        if count >= 60:
            return False

        cache.set(key, count + 1, 60)
        return True
```

---

## 3. Data Encryption

### 3.1 Stored Data Encryption

```python
# server/encryption/fields.py

from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64

class EncryptedCharField(models.CharField):
    """Encrypted character field"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cipher = Fernet(settings.ENCRYPTION_KEY)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            # Decrypt
            decrypted = self.cipher.decrypt(value.encode())
            return decrypted.decode()
        except:
            return value

    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return str(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        # Encrypt
        encrypted = self.cipher.encrypt(value.encode())
        return encrypted.decode()

# Usage example
class SensitiveData(models.Model):
    """Sensitive data model"""
    api_key = EncryptedCharField(max_length=255)
    secret_key = EncryptedCharField(max_length=255)
    credit_card_token = EncryptedCharField(max_length=255, null=True)
```

### 3.2 Communication Encryption

```python
# server/middleware/encryption.py

from django.utils.deprecation import MiddlewareMixin
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

class EncryptionMiddleware(MiddlewareMixin):
    """Communication encryption middleware"""

    def process_request(self, request):
        """Request decryption"""
        if request.META.get('HTTP_X_ENCRYPTED') == 'true':
            try:
                # Get encrypted data
                encrypted_data = request.body

                # Decrypt
                decrypted_data = self.decrypt_data(encrypted_data)

                # Replace request body
                request._body = decrypted_data

            except Exception as e:
                logger.error(f"Decryption error: {e}")

        return None

    def process_response(self, request, response):
        """Response encryption"""
        if request.META.get('HTTP_X_ENCRYPTED') == 'true':
            try:
                # Get response data
                response_data = response.content

                # Encrypt
                encrypted_data = self.encrypt_data(response_data)

                # Replace response
                response.content = encrypted_data
                response['X-Encrypted'] = 'true'

            except Exception as e:
                logger.error(f"Encryption error: {e}")

        return response

    def encrypt_data(self, data):
        """Encrypt data (AES-256-GCM)"""
        # Generate key
        key = self.get_encryption_key()

        # Generate IV
        iv = os.urandom(12)

        # Encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()

        # Combine IV + tag + ciphertext
        return iv + encryptor.tag + ciphertext

    def decrypt_data(self, encrypted_data):
        """Decrypt data"""
        # Get key
        key = self.get_encryption_key()

        # Separate IV, tag, and ciphertext
        iv = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]

        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext

    def get_encryption_key(self):
        """Get encryption key"""
        from django.conf import settings
        return base64.b64decode(settings.ENCRYPTION_KEY)
```

---

## 4. Security Settings

### 4.1 Django Security Settings

```python
# server/tms_server/settings/security.py

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Force HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_FAILURE_VIEW = 'authentication.views.csrf_failure'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Minimum 12 characters
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'authentication.validators.ComplexityValidator',  # Custom validator
    },
]

# File upload restrictions
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Allowed hosts
ALLOWED_HOSTS = [
    'tms.techcore-solutions.jp',
    '.techcore-internal.jp',
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://tms.techcore-solutions.jp",
]
CORS_ALLOW_CREDENTIALS = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Remove 'unsafe-inline' in production
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
```

### 4.2 Password Validator

```python
# server/authentication/validators.py

from django.core.exceptions import ValidationError
import re

class ComplexityValidator:
    """Password complexity validator"""

    def validate(self, password, user=None):
        # Length check
        if len(password) < 12:
            raise ValidationError('Password must be at least 12 characters long.')

        # Uppercase check
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')

        # Lowercase check
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')

        # Number check
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number.')

        # Special character check
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character.')

        # Consecutive character check
        if re.search(r'(.)\1{2,}', password):
            raise ValidationError('Cannot use the same character more than 3 times consecutively.')

        # Common password check
        common_passwords = ['password', 'admin', 'techcore', '12345']
        if any(common in password.lower() for common in common_passwords):
            raise ValidationError('Cannot use passwords containing common words.')

    def get_help_text(self):
        return (
            'Password must meet the following requirements:\n'
            '- At least 12 characters\n'
            '- At least one uppercase, lowercase, number, and special character\n'
            '- No more than 3 consecutive identical characters\n'
            '- Must not contain common words'
        )
```

---

## 5. Audit Logging

### 5.1 Audit Log Model

```python
# server/audit/models.py

from django.db import models
from django.contrib.postgres.fields import JSONField

class SecurityAuditLog(models.Model):
    """Security audit log"""

    EVENT_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('password_changed', 'Password Changed'),
        ('permission_changed', 'Permission Changed'),
        ('data_access', 'Data Access'),
        ('data_modification', 'Data Modification'),
        ('firmware_update', 'Firmware Update'),
        ('security_alert', 'Security Alert'),
    ]

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name='Event Type'
    )
    user = models.ForeignKey(
        'authentication.TMSUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='User'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='IP Address'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    details = JSONField(
        default=dict,
        verbose_name='Details'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Timestamp'
    )

    class Meta:
        verbose_name = 'Security Audit Log'
        verbose_name_plural = 'Security Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['user']),
        ]

def log_security_event(event_type, user, ip_address, details, user_agent=''):
    """Record security event log"""
    SecurityAuditLog.objects.create(
        event_type=event_type,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details
    )
```

### 5.2 Audit Middleware

```python
# server/audit/middleware.py

from django.utils.deprecation import MiddlewareMixin
from .models import log_security_event
import json

class AuditMiddleware(MiddlewareMixin):
    """Audit middleware"""

    AUDIT_URLS = [
        '/api/terminals/',
        '/api/firmware/',
        '/api/users/',
        '/api/settings/',
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Pre-view processing audit"""
        # Check audit target URL
        if any(request.path.startswith(url) for url in self.AUDIT_URLS):
            # Data access log
            if request.method == 'GET':
                log_security_event(
                    event_type='data_access',
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=self.get_client_ip(request),
                    details={
                        'path': request.path,
                        'method': request.method,
                        'query_params': dict(request.GET),
                    },
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

            # Data modification log
            elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                log_security_event(
                    event_type='data_modification',
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=self.get_client_ip(request),
                    details={
                        'path': request.path,
                        'method': request.method,
                        'body': self.get_safe_body(request),
                    },
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

        return None

    def get_client_ip(self, request):
        """Get client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def get_safe_body(self, request):
        """Get body without sensitive information"""
        try:
            body = json.loads(request.body)
            # Exclude passwords, etc.
            sensitive_fields = ['password', 'secret', 'token', 'api_key']
            for field in sensitive_fields:
                if field in body:
                    body[field] = '***REDACTED***'
            return body
        except:
            return {}
```

---

## 6. Vulnerability Countermeasures

### 6.1 SQL Injection Prevention

```python
# Always use ORM, avoid raw SQL
from django.db.models import Q

# Good example
terminals = Terminal.objects.filter(
    Q(serial_number__icontains=search_term) |
    Q(store_name__icontains=search_term)
)

# Bad example (prohibited)
# query = f"SELECT * FROM terminals WHERE serial_number LIKE '%{search_term}%'"

# If raw SQL is absolutely necessary
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT * FROM terminals WHERE serial_number = %s",
        [serial_number]  # Parameterized query
    )
```

### 6.2 XSS Prevention

```python
# Template auto-escaping
# Django templates (automatically escaped)
{{ user_input }}

# For displaying raw HTML (use carefully)
{{ user_input|safe }}  # Only for trusted data

# Embedding data in JavaScript
<script>
    var data = {{ data|json_script:"data" }};
    var dataElement = document.getElementById('data');
    var actualData = JSON.parse(dataElement.textContent);
</script>
```

### 6.3 CSRF Prevention

```html
<!-- Always include CSRF token in forms -->
<form method="post">
    {% csrf_token %}
    <input type="text" name="username">
    <button type="submit">Submit</button>
</form>
```

```python
# For Ajax requests
def get_csrf_token(request):
    """Get CSRF token API"""
    from django.middleware.csrf import get_token
    return JsonResponse({'csrf_token': get_token(request)})
```

---

## 7. Incident Response

### 7.1 Intrusion Detection

```python
# server/security/intrusion_detection.py

from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class IntrusionDetection:
    """Intrusion detection system"""

    @staticmethod
    def detect_brute_force(ip_address):
        """Detect brute force attack"""
        key = f"failed_login:{ip_address}"
        count = cache.get(key, 0)

        if count > 10:  # More than 10 failures
            logger.critical(f"Brute force attack detected: {ip_address}")

            # Auto-block IP
            IntrusionDetection.block_ip(ip_address)

            # Send alert
            send_security_alert(
                subject="Brute Force Attack Detected",
                message=f"Attack detected from IP address {ip_address}.",
                severity="high"
            )

    @staticmethod
    def detect_sql_injection(request):
        """Detect SQL injection"""
        suspicious_patterns = [
            "' OR '1'='1",
            "DROP TABLE",
            "UNION SELECT",
            "'; DELETE",
            "1=1",
            "admin'--"
        ]

        query_string = request.META.get('QUERY_STRING', '')
        body = request.body.decode('utf-8', errors='ignore')

        for pattern in suspicious_patterns:
            if pattern.lower() in query_string.lower() or pattern.lower() in body.lower():
                logger.critical(f"SQL injection attempt detected: {pattern}")

                # Block request
                raise SuspiciousOperation("Invalid request detected")

    @staticmethod
    def block_ip(ip_address):
        """Block IP address"""
        key = f"blocked_ip:{ip_address}"
        cache.set(key, True, 86400)  # Block for 24 hours

        logger.info(f"IP address blocked: {ip_address}")
```

### 7.2 Security Alerts

```python
# server/security/alerts.py

from django.core.mail import send_mail
from django.conf import settings
import requests

def send_security_alert(subject, message, severity='medium'):
    """Send security alert"""

    # Send email
    if severity in ['high', 'critical']:
        recipients = settings.SECURITY_ALERT_RECIPIENTS
        send_mail(
            subject=f"[TMS Security Alert] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

    # Slack notification (optional)
    if settings.SLACK_WEBHOOK_URL:
        color = {
            'low': '#36a64f',
            'medium': '#ff9900',
            'high': '#ff0000',
            'critical': '#000000'
        }.get(severity, '#808080')

        requests.post(settings.SLACK_WEBHOOK_URL, json={
            'attachments': [{
                'color': color,
                'title': subject,
                'text': message,
                'footer': 'TMS Security System',
            }]
        })

    # Log record
    from audit.models import log_security_event
    log_security_event(
        event_type='security_alert',
        user=None,
        ip_address='0.0.0.0',
        details={
            'subject': subject,
            'message': message,
            'severity': severity
        }
    )
```

---

## 8. Security Testing

### 8.1 Security Test Cases

```python
# tests/test_security.py

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
import time

User = get_user_model()

class SecurityTestCase(TestCase):
    """Security tests"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestP@ssw0rd123!',
            email='test@example.com'
        )

    def test_password_complexity(self):
        """Password complexity test"""
        weak_passwords = [
            'password',
            '12345678',
            'Password',
            'Password1',
            'Password123'
        ]

        for weak_password in weak_passwords:
            with self.assertRaises(ValidationError):
                user = User.objects.create_user(
                    username='weakuser',
                    password=weak_password
                )

    def test_brute_force_protection(self):
        """Brute force protection test"""
        # Consecutive login failures
        for i in range(6):
            response = self.client.post('/login/', {
                'username': 'testuser',
                'password': 'wrongpassword'
            })

        # Verify account is locked
        user = User.objects.get(username='testuser')
        self.assertTrue(user.is_locked())

    def test_sql_injection(self):
        """SQL injection test"""
        malicious_inputs = [
            "'; DROP TABLE terminals;--",
            "' OR '1'='1",
            "admin'--",
        ]

        for malicious_input in malicious_inputs:
            response = self.client.get('/api/terminals/', {
                'search': malicious_input
            })
            # Verify it doesn't error and is processed properly
            self.assertNotEqual(response.status_code, 500)

    def test_xss_prevention(self):
        """XSS prevention test"""
        self.client.login(username='testuser', password='TestP@ssw0rd123!')

        # Post malicious script
        response = self.client.post('/api/terminals/comment/', {
            'comment': '<script>alert("XSS")</script>'
        })

        # Verify script is not in response
        self.assertNotIn('<script>', response.content.decode())

    def test_session_timeout(self):
        """Session timeout test"""
        self.client.login(username='testuser', password='TestP@ssw0rd123!')

        # Verify session is valid
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Simulate timeout elapsed
        session = self.client.session
        session.set_expiry(-1)
        session.save()

        # Verify session is invalid
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/')

    def test_secure_headers(self):
        """Security headers test"""
        response = self.client.get('/')

        # Verify security headers
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertTrue('Strict-Transport-Security' in response)
```

---

## 9. Compliance

### 9.1 PCI DSS Compliance Checklist

- [ ] **Cardholder Data Protection**
  - [ ] Card number encryption
  - [ ] CVV not stored
  - [ ] Tokenization implemented

- [ ] **Access Control**
  - [ ] Principle of least privilege
  - [ ] Multi-factor authentication
  - [ ] Password policy

- [ ] **Audit Logs**
  - [ ] All access logged
  - [ ] Tamper-proof logs
  - [ ] 1+ year retention

- [ ] **Regular Testing**
  - [ ] Vulnerability scans (quarterly)
  - [ ] Penetration testing (annual)
  - [ ] Security patch application

### 9.2 GDPR Compliance

```python
# server/gdpr/views.py

@login_required
def export_personal_data(request):
    """Export personal data (GDPR compliance)"""
    user = request.user

    # Collect personal data
    personal_data = {
        'user_info': {
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat(),
        },
        'activity_logs': list(
            SecurityAuditLog.objects.filter(user=user).values()
        ),
    }

    # Download as JSON
    response = JsonResponse(personal_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="personal_data_{user.id}.json"'

    return response

@login_required
def delete_account(request):
    """Delete account (right to be forgotten)"""
    if request.method == 'POST':
        user = request.user

        # Anonymize audit logs
        SecurityAuditLog.objects.filter(user=user).update(
            user=None,
            details={'anonymized': True}
        )

        # Delete user account
        user.delete()

        return redirect('goodbye')
```

---

## Summary

With this security implementation specification:

1. **Defense in depth** security assurance
2. **PCI DSS Level 3** compliance capable
3. **Audit logs** for complete traceability
4. **Automatic threat detection** and response
5. **GDPR compliant** privacy protection

Devin can fully implement a secure TMS based on this specification.
