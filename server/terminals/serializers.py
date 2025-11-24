from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    TMSUser, Customer, Terminal, Alert, FirmwareVersion,
    UpdateTask, TerminalLog, AuditLog
)


class TMSUserSerializer(serializers.ModelSerializer):
    """Serializer for TMSUser model"""
    
    class Meta:
        model = TMSUser
        fields = ['id', 'username', 'email', 'full_name', 'role', 'is_active', 
                  'last_login', 'mfa_enabled', 'date_joined']
        read_only_fields = ['id', 'last_login', 'date_joined']


class LoginSerializer(serializers.Serializer):
    """Serializer for login request"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            data['user'] = user
        else:
            raise serializers.ValidationError('Must include "username" and "password".')
        
        return data


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    terminal_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = ['id', 'company_name', 'company_name_kana', 'contact_person', 
                  'contact_email', 'contact_phone', 'postal_code', 'address',
                  'contract_type', 'contract_start_date', 'contract_end_date',
                  'is_active', 'max_terminals', 'notes', 'terminal_count',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'terminal_count']
    
    def get_terminal_count(self, obj):
        return obj.terminals.count()


class CustomerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for customer list"""
    
    class Meta:
        model = Customer
        fields = ['id', 'company_name']


class TerminalMetricsSerializer(serializers.Serializer):
    """Serializer for terminal metrics"""
    cpu_usage = serializers.IntegerField()
    memory_usage = serializers.IntegerField()
    disk_usage = serializers.IntegerField()
    temperature = serializers.IntegerField(required=False, allow_null=True)


class TerminalSettingsSerializer(serializers.Serializer):
    """Serializer for terminal settings"""
    heartbeat_interval = serializers.IntegerField()
    auto_update_enabled = serializers.BooleanField()
    maintenance_mode = serializers.BooleanField()


class TerminalListSerializer(serializers.ModelSerializer):
    """Simplified serializer for terminal list"""
    customer = CustomerListSerializer(read_only=True)
    active_alerts = serializers.SerializerMethodField()
    
    class Meta:
        model = Terminal
        fields = ['id', 'serial_number', 'customer', 'store_name', 'status',
                  'firmware_version', 'agent_version', 'last_heartbeat',
                  'cpu_usage', 'memory_usage', 'disk_usage', 'active_alerts',
                  'installed_date']
        read_only_fields = ['id']
    
    def get_active_alerts(self, obj):
        return obj.alerts.filter(is_resolved=False).count()


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model"""
    terminal = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = ['id', 'terminal', 'alert_type', 'severity', 'title', 'message',
                  'details', 'is_acknowledged', 'acknowledged_by', 'acknowledged_at',
                  'is_resolved', 'resolved_by', 'resolved_at', 'resolution_notes',
                  'auto_resolved', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_terminal(self, obj):
        return {
            'id': obj.terminal.id,
            'serial_number': obj.terminal.serial_number,
            'store_name': obj.terminal.store_name
        }


class TerminalDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for terminal"""
    customer = CustomerSerializer(read_only=True)
    metrics = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    recent_alerts = serializers.SerializerMethodField()
    update_history = serializers.SerializerMethodField()
    
    class Meta:
        model = Terminal
        fields = ['id', 'serial_number', 'model', 'customer', 'store_name',
                  'store_code', 'installation_address', 'status', 'firmware_version',
                  'agent_version', 'ip_address', 'mac_address', 'last_heartbeat',
                  'installed_date', 'warranty_end_date', 'metrics', 'settings',
                  'recent_alerts', 'update_history', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_metrics(self, obj):
        return {
            'cpu_usage': obj.cpu_usage,
            'memory_usage': obj.memory_usage,
            'disk_usage': obj.disk_usage,
            'temperature': obj.temperature
        }
    
    def get_settings(self, obj):
        return {
            'heartbeat_interval': obj.heartbeat_interval,
            'auto_update_enabled': obj.auto_update_enabled,
            'maintenance_mode': obj.maintenance_mode
        }
    
    def get_recent_alerts(self, obj):
        alerts = obj.alerts.order_by('-created_at')[:5]
        return [{
            'id': alert.id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'title': alert.title,
            'created_at': alert.created_at,
            'is_resolved': alert.is_resolved
        } for alert in alerts]
    
    def get_update_history(self, obj):
        tasks = obj.update_tasks.filter(task_type='firmware').order_by('-completed_at')[:5]
        return [{
            'id': task.id,
            'type': task.task_type,
            'from_version': obj.firmware_version,
            'to_version': task.firmware_version.version if task.firmware_version else None,
            'status': task.status,
            'updated_at': task.completed_at
        } for task in tasks]


class FirmwareVersionSerializer(serializers.ModelSerializer):
    """Serializer for FirmwareVersion model"""
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = FirmwareVersion
        fields = ['id', 'version', 'model', 'file_name', 'file_size', 'file_size_mb',
                  'file_hash', 'file_url', 'release_notes', 'is_mandatory', 'is_latest',
                  'min_agent_version', 'released_date', 'created_at', 'created_by']
        read_only_fields = ['id', 'created_at', 'file_size_mb']
    
    def get_file_size_mb(self, obj):
        return round(obj.file_size / (1024 * 1024), 2)


class UpdateTaskSerializer(serializers.ModelSerializer):
    """Serializer for UpdateTask model"""
    terminal = TerminalListSerializer(read_only=True)
    firmware_version = FirmwareVersionSerializer(read_only=True)
    
    class Meta:
        model = UpdateTask
        fields = ['id', 'terminal', 'task_type', 'firmware_version', 'parameters',
                  'status', 'priority', 'scheduled_at', 'started_at', 'completed_at',
                  'retry_count', 'max_retries', 'error_message', 'progress',
                  'created_at', 'created_by']
        read_only_fields = ['id', 'created_at']


class TerminalLogSerializer(serializers.ModelSerializer):
    """Serializer for TerminalLog model"""
    
    class Meta:
        model = TerminalLog
        fields = ['id', 'terminal', 'log_type', 'log_level', 'message', 'details',
                  'created_at']
        read_only_fields = ['id', 'created_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model"""
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'username', 'action', 'target_type', 'target_id',
                  'ip_address', 'user_agent', 'request_method', 'request_path',
                  'request_body', 'response_status', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']


class AgentRegisterSerializer(serializers.Serializer):
    """Serializer for agent registration"""
    serial_number = serializers.CharField(max_length=50)
    model = serializers.CharField(max_length=20, default='TC-200')
    mac_address = serializers.CharField(max_length=17, required=False)
    agent_version = serializers.CharField(max_length=20)
    hostname = serializers.CharField(max_length=100, required=False)
    os_info = serializers.JSONField(required=False)


class AgentHeartbeatSerializer(serializers.Serializer):
    """Serializer for agent heartbeat"""
    serial_number = serializers.CharField(max_length=50)
    timestamp = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=['online', 'offline', 'error', 'maintenance'])
    metrics = TerminalMetricsSerializer()
    firmware_version = serializers.CharField(max_length=20)
    agent_version = serializers.CharField(max_length=20)
    ip_address = serializers.IPAddressField(required=False)
    uptime_seconds = serializers.IntegerField(required=False)
    last_transaction = serializers.DateTimeField(required=False, allow_null=True)
    transaction_count = serializers.IntegerField(required=False)


class AgentLogSerializer(serializers.Serializer):
    """Serializer for individual agent log"""
    timestamp = serializers.DateTimeField()
    level = serializers.ChoiceField(choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
    type = serializers.ChoiceField(choices=['heartbeat', 'transaction', 'error', 'communication', 'system', 'update'])
    message = serializers.CharField()
    details = serializers.JSONField(required=False)


class AgentLogsSerializer(serializers.Serializer):
    """Serializer for agent logs submission"""
    serial_number = serializers.CharField(max_length=50)
    logs = AgentLogSerializer(many=True)


class CommandResultSerializer(serializers.Serializer):
    """Serializer for command execution result"""
    serial_number = serializers.CharField(max_length=50)
    command_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['completed', 'failed', 'cancelled'])
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()
    result = serializers.JSONField(required=False)


class TerminalConfigUpdateSerializer(serializers.Serializer):
    """Serializer for terminal configuration update"""
    heartbeat_interval = serializers.IntegerField(required=False)
    auto_update_enabled = serializers.BooleanField(required=False)
    maintenance_mode = serializers.BooleanField(required=False)
    custom_settings = serializers.JSONField(required=False)


class TerminalCommandSerializer(serializers.Serializer):
    """Serializer for terminal command"""
    type = serializers.ChoiceField(choices=['reboot', 'update_firmware', 'update_config', 'diagnostic'])
    priority = serializers.ChoiceField(choices=['low', 'normal', 'high'], default='normal')
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    parameters = serializers.JSONField(required=False)
