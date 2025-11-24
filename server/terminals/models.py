from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class TMSUser(AbstractUser):
    """Custom user model for TMS with role-based access control"""
    
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
    full_name = models.CharField(max_length=100, verbose_name='Full Name')
    
    # MFA settings
    mfa_enabled = models.BooleanField(default=False, verbose_name='MFA Enabled')
    mfa_secret = models.CharField(max_length=32, blank=True, verbose_name='MFA Secret')
    
    # Security settings
    password_changed_at = models.DateTimeField(null=True, blank=True, verbose_name='Password Changed At')
    failed_login_attempts = models.IntegerField(default=0, verbose_name='Failed Login Attempts')
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name='Locked Until')
    
    # Audit information
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Last Login IP')
    
    class Meta:
        verbose_name = 'TMS User'
        verbose_name_plural = 'TMS Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Customer(models.Model):
    """Customer company master (TC-200 sales destinations)"""
    
    CONTRACT_TYPE_CHOICES = [
        ('basic', 'Basic Maintenance'),
        ('standard', 'Standard Maintenance'),
        ('premium', 'Premium Maintenance'),
    ]
    
    company_name = models.CharField(max_length=100, unique=True, verbose_name='Company Name')
    company_name_kana = models.CharField(max_length=100, blank=True, verbose_name='Company Name (Kana)')
    contact_person = models.CharField(max_length=50, verbose_name='Contact Person')
    contact_email = models.EmailField(verbose_name='Contact Email')
    contact_phone = models.CharField(max_length=20, verbose_name='Phone Number')
    postal_code = models.CharField(max_length=8, blank=True, verbose_name='Postal Code')
    address = models.TextField(blank=True, verbose_name='Address')
    
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        default='basic',
        verbose_name='Contract Type'
    )
    contract_start_date = models.DateField(verbose_name='Contract Start Date')
    contract_end_date = models.DateField(null=True, blank=True, verbose_name='Contract End Date')
    
    is_active = models.BooleanField(default=True, verbose_name='Active')
    max_terminals = models.IntegerField(default=100, verbose_name='Max Terminals')
    notes = models.TextField(blank=True, verbose_name='Notes')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    created_by = models.CharField(max_length=50, blank=True, verbose_name='Created By')
    updated_by = models.CharField(max_length=50, blank=True, verbose_name='Updated By')
    
    class Meta:
        verbose_name = 'Customer Company'
        verbose_name_plural = 'Customer Companies'
        ordering = ['company_name']
    
    def __str__(self):
        return self.company_name


class Terminal(models.Model):
    """Terminal master"""
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
        ('maintenance', 'Under Maintenance'),
    ]
    
    serial_number = models.CharField(max_length=50, unique=True, verbose_name='Serial Number')
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='terminals',
        verbose_name='Customer Company'
    )
    model = models.CharField(max_length=20, default='TC-200', verbose_name='Model')
    store_name = models.CharField(max_length=100, verbose_name='Installation Store Name')
    store_code = models.CharField(max_length=20, blank=True, verbose_name='Store Code')
    installation_address = models.TextField(blank=True, verbose_name='Installation Address')
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name='Status'
    )
    
    firmware_version = models.CharField(max_length=20, default='1.0.0', verbose_name='Firmware Version')
    agent_version = models.CharField(max_length=20, blank=True, verbose_name='Agent Version')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Address')
    mac_address = models.CharField(max_length=17, blank=True, verbose_name='MAC Address')
    
    last_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name='Last Heartbeat')
    installed_date = models.DateField(null=True, blank=True, verbose_name='Installation Date')
    warranty_end_date = models.DateField(null=True, blank=True, verbose_name='Warranty End Date')
    
    # Metrics
    cpu_usage = models.SmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='CPU Usage (%)'
    )
    memory_usage = models.SmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Memory Usage (%)'
    )
    disk_usage = models.SmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Disk Usage (%)'
    )
    temperature = models.SmallIntegerField(null=True, blank=True, verbose_name='Temperature (°C)')
    
    # Settings
    heartbeat_interval = models.IntegerField(default=300, verbose_name='Heartbeat Interval (seconds)')
    auto_update_enabled = models.BooleanField(default=True, verbose_name='Auto Update Enabled')
    maintenance_mode = models.BooleanField(default=False, verbose_name='Maintenance Mode')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Terminal'
        verbose_name_plural = 'Terminals'
        ordering = ['customer', 'store_name']
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['customer', 'store_name']),
            models.Index(fields=['status']),
            models.Index(fields=['last_heartbeat']),
        ]
    
    def __str__(self):
        return f'{self.serial_number} ({self.customer.company_name} - {self.store_name})'


class Alert(models.Model):
    """Alert (incident notification)"""
    
    ALERT_TYPE_CHOICES = [
        ('offline', 'Offline'),
        ('error', 'Error'),
        ('high_cpu', 'High CPU Usage'),
        ('high_memory', 'High Memory Usage'),
        ('high_disk', 'High Disk Usage'),
        ('update_failed', 'Update Failed'),
        ('connection_lost', 'Connection Lost'),
    ]
    
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INFO', 'Information'),
    ]
    
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='Terminal'
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, verbose_name='Alert Type')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM', verbose_name='Severity')
    title = models.CharField(max_length=200, verbose_name='Title')
    message = models.TextField(verbose_name='Message')
    details = models.JSONField(null=True, blank=True, verbose_name='Details')
    
    is_acknowledged = models.BooleanField(default=False, verbose_name='Acknowledged')
    acknowledged_by = models.CharField(max_length=50, blank=True, verbose_name='Acknowledged By')
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name='Acknowledged At')
    
    is_resolved = models.BooleanField(default=False, verbose_name='Resolved')
    resolved_by = models.CharField(max_length=50, blank=True, verbose_name='Resolved By')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Resolved At')
    resolution_notes = models.TextField(blank=True, verbose_name='Resolution Notes')
    auto_resolved = models.BooleanField(default=False, verbose_name='Auto Resolved')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['terminal']),
            models.Index(fields=['is_resolved']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['severity'], condition=models.Q(is_resolved=False), name='alert_severity_unresolved_idx'),
            models.Index(fields=['alert_type']),
        ]
    
    def __str__(self):
        return f'{self.get_severity_display()}: {self.title} - {self.terminal.serial_number}'


class FirmwareVersion(models.Model):
    """Firmware versions"""
    
    version = models.CharField(max_length=20, unique=True, verbose_name='Version')
    model = models.CharField(max_length=20, default='TC-200', verbose_name='Model')
    file_name = models.CharField(max_length=255, verbose_name='File Name')
    file_size = models.BigIntegerField(verbose_name='File Size (bytes)')
    file_hash = models.CharField(max_length=64, verbose_name='File Hash (SHA256)')
    file_url = models.TextField(blank=True, verbose_name='File URL')
    
    release_notes = models.TextField(blank=True, verbose_name='Release Notes')
    is_mandatory = models.BooleanField(default=False, verbose_name='Mandatory Update')
    is_latest = models.BooleanField(default=False, verbose_name='Latest Version')
    min_agent_version = models.CharField(max_length=20, blank=True, verbose_name='Minimum Agent Version')
    
    released_date = models.DateField(verbose_name='Release Date')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    created_by = models.CharField(max_length=50, blank=True, verbose_name='Created By')
    
    class Meta:
        verbose_name = 'Firmware Version'
        verbose_name_plural = 'Firmware Versions'
        ordering = ['-released_date']
        indexes = [
            models.Index(fields=['version', 'model']),
            models.Index(fields=['is_latest'], condition=models.Q(is_latest=True), name='firmware_latest_idx'),
        ]
    
    def __str__(self):
        return f'{self.model} v{self.version}'


class UpdateTask(models.Model):
    """Update tasks"""
    
    TASK_TYPE_CHOICES = [
        ('firmware', 'Firmware Update'),
        ('config', 'Configuration Update'),
        ('reboot', 'Reboot'),
        ('diagnostic', 'Diagnostic'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name='update_tasks',
        verbose_name='Terminal'
    )
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name='Task Type')
    firmware_version = models.ForeignKey(
        FirmwareVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Firmware Version'
    )
    parameters = models.JSONField(null=True, blank=True, verbose_name='Parameters')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    priority = models.IntegerField(default=5, verbose_name='Priority')
    
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='Scheduled At')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started At')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed At')
    
    retry_count = models.IntegerField(default=0, verbose_name='Retry Count')
    max_retries = models.IntegerField(default=3, verbose_name='Max Retries')
    error_message = models.TextField(blank=True, verbose_name='Error Message')
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Progress (%)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    created_by = models.CharField(max_length=50, blank=True, verbose_name='Created By')
    
    class Meta:
        verbose_name = 'Update Task'
        verbose_name_plural = 'Update Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['terminal']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_at'], condition=models.Q(status='pending'), name='updatetask_sched_pending_idx'),
            models.Index(fields=['priority', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f'{self.get_task_type_display()} - {self.terminal.serial_number} ({self.get_status_display()})'


class TerminalLog(models.Model):
    """Terminal logs"""
    
    LOG_TYPE_CHOICES = [
        ('heartbeat', 'Heartbeat'),
        ('transaction', 'Transaction'),
        ('error', 'Error'),
        ('communication', 'Communication'),
        ('system', 'System'),
        ('update', 'Update'),
    ]
    
    LOG_LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='Terminal'
    )
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, verbose_name='Log Type')
    log_level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, default='INFO', verbose_name='Log Level')
    message = models.TextField(verbose_name='Message')
    details = models.JSONField(null=True, blank=True, verbose_name='Details')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Terminal Log'
        verbose_name_plural = 'Terminal Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['terminal']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['log_type']),
            models.Index(fields=['log_level'], condition=models.Q(log_level__in=['ERROR', 'CRITICAL']), name='terminallog_error_critical_idx'),
        ]
    
    def __str__(self):
        return f'{self.terminal.serial_number} - {self.get_log_level_display()}: {self.message[:50]}'


class AuditLog(models.Model):
    """Audit logs for security tracking"""
    
    user = models.ForeignKey(
        TMSUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='User'
    )
    username = models.CharField(max_length=50, blank=True, verbose_name='Username')
    action = models.CharField(max_length=50, verbose_name='Action')
    target_type = models.CharField(max_length=50, blank=True, verbose_name='Target Type')
    target_id = models.IntegerField(null=True, blank=True, verbose_name='Target ID')
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Address')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    request_method = models.CharField(max_length=10, blank=True, verbose_name='Request Method')
    request_path = models.TextField(blank=True, verbose_name='Request Path')
    request_body = models.JSONField(null=True, blank=True, verbose_name='Request Body')
    response_status = models.IntegerField(null=True, blank=True, verbose_name='Response Status')
    details = models.JSONField(null=True, blank=True, verbose_name='Details')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['target_type', 'target_id']),
        ]
    
    def __str__(self):
        return f'{self.username} - {self.action} at {self.created_at}'
