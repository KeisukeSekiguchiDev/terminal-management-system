# セキュリティ実装仕様書
## Terminal Management System (TMS)

**文書バージョン**: 1.0
**作成日**: 2025年11月24日
**セキュリティレベル**: 高（金融端末管理）

---

## 1. セキュリティ概要

### 1.1 セキュリティ要件

| 分類 | 要件 | 対応レベル |
|------|------|-----------|
| 認証 | 多要素認証（MFA）対応 | 必須 |
| 暗号化 | 通信・保存データの暗号化 | 必須 |
| アクセス制御 | ロールベースアクセス制御 | 必須 |
| 監査 | 全操作のログ記録 | 必須 |
| PCI DSS | Level 3準拠 | 推奨 |

### 1.2 脅威モデル

```
攻撃者 → [インターネット] → ALB → EC2 → RDS
   ↓                            ↓
   └→ [店舗PC] → エージェント → TC-200端末

主な脅威:
1. 不正アクセス（管理画面への侵入）
2. データ漏洩（顧客情報・端末情報）
3. 改ざん（ファームウェア・設定）
4. DoS攻撃（サービス停止）
5. 中間者攻撃（通信傍受）
```

---

## 2. 認証・認可実装

### 2.1 ユーザー認証 (Django)

```python
# server/authentication/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
import pyotp
import qrcode
from io import BytesIO
import base64

class TMSUser(AbstractUser):
    """カスタムユーザーモデル"""

    ROLE_CHOICES = [
        ('admin', 'システム管理者'),
        ('operator', '運用オペレーター'),
        ('support', 'サポート担当'),
        ('viewer', '閲覧のみ'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name='役割'
    )

    # MFA設定
    mfa_enabled = models.BooleanField(
        default=False,
        verbose_name='MFA有効'
    )
    mfa_secret = models.CharField(
        max_length=32,
        blank=True,
        verbose_name='MFAシークレット'
    )

    # セキュリティ設定
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='パスワード変更日時'
    )
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name='ログイン失敗回数'
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='ロック解除日時'
    )

    # 監査情報
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='最終ログインIP'
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name='作成者'
    )

    class Meta:
        verbose_name = 'TMSユーザー'
        verbose_name_plural = 'TMSユーザー'

    def generate_mfa_secret(self):
        """MFAシークレット生成"""
        self.mfa_secret = pyotp.random_base32()
        self.save()
        return self.mfa_secret

    def get_mfa_qr_code(self):
        """MFA QRコード生成"""
        if not self.mfa_secret:
            self.generate_mfa_secret()

        provisioning_uri = pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email,
            issuer_name='TechCore TMS'
        )

        # QRコード生成
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    def verify_mfa_token(self, token):
        """MFAトークン検証"""
        if not self.mfa_enabled or not self.mfa_secret:
            return True

        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)

    def is_locked(self):
        """アカウントロック状態確認"""
        from django.utils import timezone

        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def increment_failed_login(self):
        """ログイン失敗カウント増加"""
        from django.utils import timezone
        from datetime import timedelta

        self.failed_login_attempts += 1

        # 5回失敗で30分ロック
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=30)

        self.save()

    def reset_failed_login(self):
        """ログイン失敗カウントリセット"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save()
```

### 2.2 認証ビュー実装

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
    """ログインビュー（MFA対応）"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        mfa_token = request.POST.get('mfa_token', '')

        # IPアドレス取得
        ip_address = get_client_ip(request)

        try:
            user = TMSUser.objects.get(username=username)

            # アカウントロック確認
            if user.is_locked():
                logger.warning(f"ロックされたアカウントへのアクセス試行: {username} from {ip_address}")
                messages.error(request, 'アカウントがロックされています。しばらく待ってから再試行してください。')
                return render(request, 'authentication/login.html')

            # 認証
            user = authenticate(request, username=username, password=password)

            if user:
                # MFA検証
                if user.mfa_enabled:
                    if not user.verify_mfa_token(mfa_token):
                        user.increment_failed_login()
                        logger.warning(f"MFA認証失敗: {username} from {ip_address}")
                        messages.error(request, '認証コードが正しくありません。')
                        return render(request, 'authentication/login.html')

                # ログイン成功
                login(request, user)
                user.last_login_ip = ip_address
                user.reset_failed_login()
                user.save()

                # セッション設定
                request.session.set_expiry(3600)  # 1時間
                request.session['user_role'] = user.role

                # 監査ログ
                log_security_event(
                    event_type='login_success',
                    user=user,
                    ip_address=ip_address,
                    details={'username': username}
                )

                logger.info(f"ログイン成功: {username} from {ip_address}")
                return redirect('dashboard')
            else:
                # ログイン失敗
                if TMSUser.objects.filter(username=username).exists():
                    user = TMSUser.objects.get(username=username)
                    user.increment_failed_login()

                log_security_event(
                    event_type='login_failed',
                    user=None,
                    ip_address=ip_address,
                    details={'username': username}
                )

                logger.warning(f"ログイン失敗: {username} from {ip_address}")
                messages.error(request, 'ユーザー名またはパスワードが正しくありません。')

        except TMSUser.DoesNotExist:
            logger.warning(f"存在しないユーザーへのログイン試行: {username} from {ip_address}")
            messages.error(request, 'ユーザー名またはパスワードが正しくありません。')

    return render(request, 'authentication/login.html')

@login_required
@csrf_protect
def logout_view(request):
    """ログアウト"""
    user = request.user
    ip_address = get_client_ip(request)

    # 監査ログ
    log_security_event(
        event_type='logout',
        user=user,
        ip_address=ip_address,
        details={}
    )

    logout(request)
    logger.info(f"ログアウト: {user.username} from {ip_address}")

    return redirect('login')

def get_client_ip(request):
    """クライアントIPアドレス取得"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 2.3 ロールベースアクセス制御

```python
# server/authentication/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def require_role(*allowed_roles):
    """ロール必須デコレーター"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if request.user.role not in allowed_roles:
                messages.error(request, 'このページへのアクセス権限がありません。')
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

# 使用例
@login_required
@require_role('admin', 'operator')
def firmware_update_view(request):
    """ファームウェア更新画面（管理者・オペレーターのみ）"""
    pass
```

### 2.4 API認証（エージェント用）

```python
# server/api/authentication.py

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache
import hashlib
import hmac
import time

class AgentAuthentication(BaseAuthentication):
    """エージェント認証"""

    def authenticate(self, request):
        # APIキーヘッダー取得
        api_key = request.META.get('HTTP_X_API_KEY')
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')

        if not all([api_key, signature, timestamp]):
            return None

        # タイムスタンプ検証（5分以内）
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            raise AuthenticationFailed('リクエストが期限切れです')

        # エージェント検索
        try:
            from terminals.models import Terminal
            terminal = Terminal.objects.get(api_key=api_key)
        except Terminal.DoesNotExist:
            raise AuthenticationFailed('無効なAPIキー')

        # 署名検証
        expected_signature = self.generate_signature(
            api_key=api_key,
            secret_key=terminal.secret_key,
            timestamp=timestamp,
            body=request.body.decode('utf-8')
        )

        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationFailed('署名が無効です')

        # レート制限チェック
        if not self.check_rate_limit(api_key):
            raise AuthenticationFailed('レート制限を超えました')

        return (terminal, None)

    def generate_signature(self, api_key, secret_key, timestamp, body):
        """署名生成"""
        message = f"{api_key}:{timestamp}:{body}"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def check_rate_limit(self, api_key):
        """レート制限チェック（1分間に60リクエストまで）"""
        key = f"rate_limit:{api_key}"
        count = cache.get(key, 0)

        if count >= 60:
            return False

        cache.set(key, count + 1, 60)
        return True
```

---

## 3. データ暗号化

### 3.1 保存データ暗号化

```python
# server/encryption/fields.py

from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64

class EncryptedCharField(models.CharField):
    """暗号化文字フィールド"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cipher = Fernet(settings.ENCRYPTION_KEY)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            # 復号化
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
        # 暗号化
        encrypted = self.cipher.encrypt(value.encode())
        return encrypted.decode()

# 使用例
class SensitiveData(models.Model):
    """機密データモデル"""
    api_key = EncryptedCharField(max_length=255)
    secret_key = EncryptedCharField(max_length=255)
    credit_card_token = EncryptedCharField(max_length=255, null=True)
```

### 3.2 通信暗号化

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
    """通信暗号化ミドルウェア"""

    def process_request(self, request):
        """リクエスト復号化"""
        if request.META.get('HTTP_X_ENCRYPTED') == 'true':
            try:
                # 暗号化データ取得
                encrypted_data = request.body

                # 復号化
                decrypted_data = self.decrypt_data(encrypted_data)

                # リクエストボディ置換
                request._body = decrypted_data

            except Exception as e:
                logger.error(f"復号化エラー: {e}")

        return None

    def process_response(self, request, response):
        """レスポンス暗号化"""
        if request.META.get('HTTP_X_ENCRYPTED') == 'true':
            try:
                # レスポンスデータ取得
                response_data = response.content

                # 暗号化
                encrypted_data = self.encrypt_data(response_data)

                # レスポンス置換
                response.content = encrypted_data
                response['X-Encrypted'] = 'true'

            except Exception as e:
                logger.error(f"暗号化エラー: {e}")

        return response

    def encrypt_data(self, data):
        """データ暗号化（AES-256-GCM）"""
        # 鍵生成
        key = self.get_encryption_key()

        # IV生成
        iv = os.urandom(12)

        # 暗号化
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()

        # IV + タグ + 暗号文を結合
        return iv + encryptor.tag + ciphertext

    def decrypt_data(self, encrypted_data):
        """データ復号化"""
        # 鍵取得
        key = self.get_encryption_key()

        # IV、タグ、暗号文を分離
        iv = encrypted_data[:12]
        tag = encrypted_data[12:28]
        ciphertext = encrypted_data[28:]

        # 復号化
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext

    def get_encryption_key(self):
        """暗号化キー取得"""
        from django.conf import settings
        return base64.b64decode(settings.ENCRYPTION_KEY)
```

---

## 4. セキュリティ設定

### 4.1 Django セキュリティ設定

```python
# server/tms_server/settings/security.py

# セキュリティヘッダー
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS強制
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# セッション設定
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600  # 1時間
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF設定
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_FAILURE_VIEW = 'authentication.views.csrf_failure'

# パスワードバリデーション
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # 最小12文字
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'authentication.validators.ComplexityValidator',  # カスタムバリデーター
    },
]

# ファイルアップロード制限
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# 許可するホスト
ALLOWED_HOSTS = [
    'tms.techcore-solutions.jp',
    '.techcore-internal.jp',
]

# CORS設定
CORS_ALLOWED_ORIGINS = [
    "https://tms.techcore-solutions.jp",
]
CORS_ALLOW_CREDENTIALS = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # 本番では'unsafe-inline'を削除
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
```

### 4.2 パスワードバリデーター

```python
# server/authentication/validators.py

from django.core.exceptions import ValidationError
import re

class ComplexityValidator:
    """パスワード複雑性バリデーター"""

    def validate(self, password, user=None):
        # 長さチェック
        if len(password) < 12:
            raise ValidationError('パスワードは12文字以上である必要があります。')

        # 大文字チェック
        if not re.search(r'[A-Z]', password):
            raise ValidationError('パスワードには少なくとも1つの大文字を含める必要があります。')

        # 小文字チェック
        if not re.search(r'[a-z]', password):
            raise ValidationError('パスワードには少なくとも1つの小文字を含める必要があります。')

        # 数字チェック
        if not re.search(r'\d', password):
            raise ValidationError('パスワードには少なくとも1つの数字を含める必要があります。')

        # 特殊文字チェック
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('パスワードには少なくとも1つの特殊文字を含める必要があります。')

        # 連続文字チェック
        if re.search(r'(.)\1{2,}', password):
            raise ValidationError('同じ文字を3回以上連続で使用することはできません。')

        # よく使われるパスワードチェック
        common_passwords = ['password', 'admin', 'techcore', '12345']
        if any(common in password.lower() for common in common_passwords):
            raise ValidationError('よく使われる単語を含むパスワードは使用できません。')

    def get_help_text(self):
        return (
            'パスワードは以下の条件を満たす必要があります：\n'
            '• 12文字以上\n'
            '• 大文字・小文字・数字・特殊文字を各1文字以上含む\n'
            '• 同じ文字の3回以上の連続使用禁止\n'
            '• よく使われる単語を含まない'
        )
```

---

## 5. 監査ログ

### 5.1 監査ログモデル

```python
# server/audit/models.py

from django.db import models
from django.contrib.postgres.fields import JSONField

class SecurityAuditLog(models.Model):
    """セキュリティ監査ログ"""

    EVENT_TYPES = [
        ('login_success', 'ログイン成功'),
        ('login_failed', 'ログイン失敗'),
        ('logout', 'ログアウト'),
        ('password_changed', 'パスワード変更'),
        ('permission_changed', '権限変更'),
        ('data_access', 'データアクセス'),
        ('data_modification', 'データ変更'),
        ('firmware_update', 'ファームウェア更新'),
        ('security_alert', 'セキュリティアラート'),
    ]

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name='イベント種別'
    )
    user = models.ForeignKey(
        'authentication.TMSUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ユーザー'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='IPアドレス'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='ユーザーエージェント'
    )
    details = JSONField(
        default=dict,
        verbose_name='詳細'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='タイムスタンプ'
    )

    class Meta:
        verbose_name = 'セキュリティ監査ログ'
        verbose_name_plural = 'セキュリティ監査ログ'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['user']),
        ]

def log_security_event(event_type, user, ip_address, details, user_agent=''):
    """セキュリティイベントログ記録"""
    SecurityAuditLog.objects.create(
        event_type=event_type,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details
    )
```

### 5.2 監査ミドルウェア

```python
# server/audit/middleware.py

from django.utils.deprecation import MiddlewareMixin
from .models import log_security_event
import json

class AuditMiddleware(MiddlewareMixin):
    """監査ミドルウェア"""

    AUDIT_URLS = [
        '/api/terminals/',
        '/api/firmware/',
        '/api/users/',
        '/api/settings/',
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        """ビュー処理前の監査"""
        # 監査対象URLチェック
        if any(request.path.startswith(url) for url in self.AUDIT_URLS):
            # データアクセスログ
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

            # データ変更ログ
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
        """クライアントIP取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def get_safe_body(self, request):
        """センシティブ情報を除いたボディ取得"""
        try:
            body = json.loads(request.body)
            # パスワードなどを除外
            sensitive_fields = ['password', 'secret', 'token', 'api_key']
            for field in sensitive_fields:
                if field in body:
                    body[field] = '***REDACTED***'
            return body
        except:
            return {}
```

---

## 6. 脆弱性対策

### 6.1 SQLインジェクション対策

```python
# 常にORMを使用し、生SQLは避ける
from django.db.models import Q

# 良い例
terminals = Terminal.objects.filter(
    Q(serial_number__icontains=search_term) |
    Q(store_name__icontains=search_term)
)

# 悪い例（使用禁止）
# query = f"SELECT * FROM terminals WHERE serial_number LIKE '%{search_term}%'"

# どうしても生SQLが必要な場合
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT * FROM terminals WHERE serial_number = %s",
        [serial_number]  # パラメータ化クエリ
    )
```

### 6.2 XSS対策

```python
# テンプレート自動エスケープ
# Django templates (自動的にエスケープされる)
{{ user_input }}

# 生HTMLを表示する場合（慎重に使用）
{{ user_input|safe }}  # 信頼できるデータのみ

# JavaScriptへのデータ埋め込み
<script>
    var data = {{ data|json_script:"data" }};
    var dataElement = document.getElementById('data');
    var actualData = JSON.parse(dataElement.textContent);
</script>
```

### 6.3 CSRF対策

```html
<!-- フォームには必ずCSRFトークンを含める -->
<form method="post">
    {% csrf_token %}
    <input type="text" name="username">
    <button type="submit">送信</button>
</form>
```

```python
# Ajaxリクエスト用
def get_csrf_token(request):
    """CSRFトークン取得API"""
    from django.middleware.csrf import get_token
    return JsonResponse({'csrf_token': get_token(request)})
```

---

## 7. インシデント対応

### 7.1 侵入検知

```python
# server/security/intrusion_detection.py

from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class IntrusionDetection:
    """侵入検知システム"""

    @staticmethod
    def detect_brute_force(ip_address):
        """ブルートフォース攻撃検知"""
        key = f"failed_login:{ip_address}"
        count = cache.get(key, 0)

        if count > 10:  # 10回以上の失敗
            logger.critical(f"ブルートフォース攻撃検知: {ip_address}")

            # IP自動ブロック
            IntrusionDetection.block_ip(ip_address)

            # アラート送信
            send_security_alert(
                subject="ブルートフォース攻撃検知",
                message=f"IPアドレス {ip_address} からの攻撃を検知しました。",
                severity="high"
            )

    @staticmethod
    def detect_sql_injection(request):
        """SQLインジェクション検知"""
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
                logger.critical(f"SQLインジェクション試行検知: {pattern}")

                # リクエストブロック
                raise SuspiciousOperation("不正なリクエストが検出されました")

    @staticmethod
    def block_ip(ip_address):
        """IPアドレスブロック"""
        key = f"blocked_ip:{ip_address}"
        cache.set(key, True, 86400)  # 24時間ブロック

        logger.info(f"IPアドレスをブロック: {ip_address}")
```

### 7.2 セキュリティアラート

```python
# server/security/alerts.py

from django.core.mail import send_mail
from django.conf import settings
import requests

def send_security_alert(subject, message, severity='medium'):
    """セキュリティアラート送信"""

    # メール送信
    if severity in ['high', 'critical']:
        recipients = settings.SECURITY_ALERT_RECIPIENTS
        send_mail(
            subject=f"[TMS Security Alert] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

    # Slack通知（オプション）
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

    # ログ記録
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

## 8. セキュリティテスト

### 8.1 セキュリティテストケース

```python
# tests/test_security.py

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
import time

User = get_user_model()

class SecurityTestCase(TestCase):
    """セキュリティテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestP@ssw0rd123!',
            email='test@example.com'
        )

    def test_password_complexity(self):
        """パスワード複雑性テスト"""
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
        """ブルートフォース保護テスト"""
        # 連続ログイン失敗
        for i in range(6):
            response = self.client.post('/login/', {
                'username': 'testuser',
                'password': 'wrongpassword'
            })

        # アカウントロック確認
        user = User.objects.get(username='testuser')
        self.assertTrue(user.is_locked())

    def test_sql_injection(self):
        """SQLインジェクションテスト"""
        malicious_inputs = [
            "'; DROP TABLE terminals;--",
            "' OR '1'='1",
            "admin'--",
        ]

        for malicious_input in malicious_inputs:
            response = self.client.get('/api/terminals/', {
                'search': malicious_input
            })
            # エラーにならず、適切に処理されることを確認
            self.assertNotEqual(response.status_code, 500)

    def test_xss_prevention(self):
        """XSS防止テスト"""
        self.client.login(username='testuser', password='TestP@ssw0rd123!')

        # 悪意のあるスクリプト投稿
        response = self.client.post('/api/terminals/comment/', {
            'comment': '<script>alert("XSS")</script>'
        })

        # レスポンスにスクリプトが含まれないことを確認
        self.assertNotIn('<script>', response.content.decode())

    def test_session_timeout(self):
        """セッションタイムアウトテスト"""
        self.client.login(username='testuser', password='TestP@ssw0rd123!')

        # セッション有効確認
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

        # タイムアウト時間経過をシミュレート
        session = self.client.session
        session.set_expiry(-1)
        session.save()

        # セッション無効確認
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/')

    def test_secure_headers(self):
        """セキュリティヘッダーテスト"""
        response = self.client.get('/')

        # セキュリティヘッダー確認
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertTrue('Strict-Transport-Security' in response)
```

---

## 9. コンプライアンス

### 9.1 PCI DSS準拠チェックリスト

- [ ] **カード会員データの保護**
  - [ ] カード番号の暗号化
  - [ ] CVVの非保存
  - [ ] トークン化実装

- [ ] **アクセス制御**
  - [ ] 最小権限の原則
  - [ ] 多要素認証
  - [ ] パスワードポリシー

- [ ] **監査ログ**
  - [ ] 全アクセスのログ記録
  - [ ] ログの改ざん防止
  - [ ] 1年以上の保持

- [ ] **定期的なテスト**
  - [ ] 脆弱性スキャン（四半期）
  - [ ] ペネトレーションテスト（年次）
  - [ ] セキュリティパッチ適用

### 9.2 GDPR対応

```python
# server/gdpr/views.py

@login_required
def export_personal_data(request):
    """個人データエクスポート（GDPR対応）"""
    user = request.user

    # 個人データ収集
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

    # JSON形式でダウンロード
    response = JsonResponse(personal_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="personal_data_{user.id}.json"'

    return response

@login_required
def delete_account(request):
    """アカウント削除（忘れられる権利）"""
    if request.method == 'POST':
        user = request.user

        # 監査ログは匿名化
        SecurityAuditLog.objects.filter(user=user).update(
            user=None,
            details={'anonymized': True}
        )

        # ユーザーアカウント削除
        user.delete()

        return redirect('goodbye')
```

---

## まとめ

このセキュリティ実装仕様書により：

1. **多層防御**によるセキュリティ確保
2. **PCI DSS Level 3**準拠可能
3. **監査ログ**による完全なトレーサビリティ
4. **自動脅威検知**と対応
5. **GDPR対応**のプライバシー保護

これでDevinが完全にセキュアなTMSを実装できます。