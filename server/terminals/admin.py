from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    TMSUser, Customer, Terminal, Alert, FirmwareVersion,
    UpdateTask, TerminalLog, AuditLog
)


@admin.register(TMSUser)
class TMSUserAdmin(UserAdmin):
    """Admin configuration for TMSUser"""
    list_display = ['username', 'email', 'full_name', 'role', 'is_active', 'last_login', 'mfa_enabled']
    list_filter = ['role', 'is_active', 'mfa_enabled', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'full_name']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('TMS Information', {
            'fields': ('role', 'full_name')
        }),
        ('Security', {
            'fields': ('mfa_enabled', 'mfa_secret', 'password_changed_at', 
                      'failed_login_attempts', 'locked_until', 'last_login_ip')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('TMS Information', {
            'fields': ('role', 'full_name', 'email')
        }),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin configuration for Customer"""
    list_display = ['company_name', 'contact_person', 'contact_email', 'contract_type', 
                    'is_active', 'terminal_count', 'created_at']
    list_filter = ['contract_type', 'is_active', 'created_at']
    search_fields = ['company_name', 'company_name_kana', 'contact_person', 'contact_email']
    ordering = ['company_name']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'company_name_kana')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'contact_email', 'contact_phone', 
                      'postal_code', 'address')
        }),
        ('Contract Information', {
            'fields': ('contract_type', 'contract_start_date', 'contract_end_date',
                      'is_active', 'max_terminals')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def terminal_count(self, obj):
        """Display terminal count"""
        return obj.terminals.count()
    terminal_count.short_description = 'Terminals'


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    """Admin configuration for Terminal"""
    list_display = ['serial_number', 'customer', 'store_name', 'status', 
                    'firmware_version', 'last_heartbeat', 'cpu_usage', 'memory_usage']
    list_filter = ['status', 'model', 'auto_update_enabled', 'maintenance_mode', 
                   'customer', 'created_at']
    search_fields = ['serial_number', 'store_name', 'store_code', 'customer__company_name']
    ordering = ['-last_heartbeat']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('serial_number', 'customer', 'model', 'store_name', 
                      'store_code', 'installation_address')
        }),
        ('Status', {
            'fields': ('status', 'last_heartbeat', 'installed_date', 'warranty_end_date')
        }),
        ('Software Versions', {
            'fields': ('firmware_version', 'agent_version')
        }),
        ('Network Information', {
            'fields': ('ip_address', 'mac_address')
        }),
        ('Metrics', {
            'fields': ('cpu_usage', 'memory_usage', 'disk_usage', 'temperature')
        }),
        ('Settings', {
            'fields': ('heartbeat_interval', 'auto_update_enabled', 'maintenance_mode')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('customer')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin configuration for Alert"""
    list_display = ['terminal', 'alert_type', 'severity', 'title', 
                    'is_acknowledged', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_acknowledged', 'is_resolved', 
                   'auto_resolved', 'created_at']
    search_fields = ['terminal__serial_number', 'title', 'message', 
                    'terminal__customer__company_name']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('terminal', 'alert_type', 'severity', 'title', 'message', 'details')
        }),
        ('Acknowledgement', {
            'fields': ('is_acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_by', 'resolved_at', 
                      'resolution_notes', 'auto_resolved')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('terminal', 'terminal__customer')


@admin.register(FirmwareVersion)
class FirmwareVersionAdmin(admin.ModelAdmin):
    """Admin configuration for FirmwareVersion"""
    list_display = ['version', 'model', 'is_latest', 'is_mandatory', 
                    'released_date', 'file_size_mb', 'created_at']
    list_filter = ['model', 'is_latest', 'is_mandatory', 'released_date']
    search_fields = ['version', 'model', 'release_notes']
    ordering = ['-released_date']
    date_hierarchy = 'released_date'
    
    fieldsets = (
        ('Version Information', {
            'fields': ('version', 'model', 'is_latest', 'is_mandatory', 
                      'min_agent_version', 'released_date')
        }),
        ('File Information', {
            'fields': ('file_name', 'file_size', 'file_hash', 'file_url')
        }),
        ('Release Notes', {
            'fields': ('release_notes',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def file_size_mb(self, obj):
        """Display file size in MB"""
        return f"{obj.file_size / (1024 * 1024):.2f} MB"
    file_size_mb.short_description = 'File Size'


@admin.register(UpdateTask)
class UpdateTaskAdmin(admin.ModelAdmin):
    """Admin configuration for UpdateTask"""
    list_display = ['terminal', 'task_type', 'status', 'priority', 'progress',
                    'scheduled_at', 'created_at']
    list_filter = ['task_type', 'status', 'priority', 'created_at', 'scheduled_at']
    search_fields = ['terminal__serial_number', 'terminal__customer__company_name', 
                    'error_message']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Task Information', {
            'fields': ('terminal', 'task_type', 'firmware_version', 'parameters')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'progress')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'started_at', 'completed_at')
        }),
        ('Error Handling', {
            'fields': ('retry_count', 'max_retries', 'error_message')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('terminal', 'terminal__customer', 'firmware_version')


@admin.register(TerminalLog)
class TerminalLogAdmin(admin.ModelAdmin):
    """Admin configuration for TerminalLog"""
    list_display = ['terminal', 'log_type', 'log_level', 'message_preview', 'created_at']
    list_filter = ['log_type', 'log_level', 'created_at']
    search_fields = ['terminal__serial_number', 'message', 'terminal__customer__company_name']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Log Information', {
            'fields': ('terminal', 'log_type', 'log_level', 'message', 'details')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        """Display message preview"""
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('terminal', 'terminal__customer')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for AuditLog"""
    list_display = ['username', 'action', 'target_type', 'target_id', 
                    'ip_address', 'response_status', 'created_at']
    list_filter = ['action', 'target_type', 'response_status', 'created_at']
    search_fields = ['username', 'action', 'target_type', 'ip_address', 'request_path']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'username', 'ip_address', 'user_agent')
        }),
        ('Action Information', {
            'fields': ('action', 'target_type', 'target_id')
        }),
        ('Request Information', {
            'fields': ('request_method', 'request_path', 'request_body', 'response_status')
        }),
        ('Additional Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
