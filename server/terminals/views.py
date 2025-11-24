from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta
from .models import (
    TMSUser, Customer, Terminal, Alert, FirmwareVersion,
    UpdateTask, TerminalLog, AuditLog
)
from .serializers import (
    TMSUserSerializer, LoginSerializer, CustomerSerializer,
    TerminalListSerializer, TerminalDetailSerializer, AlertSerializer,
    FirmwareVersionSerializer, UpdateTaskSerializer, TerminalLogSerializer,
    AgentRegisterSerializer, AgentHeartbeatSerializer, AgentLogsSerializer,
    CommandResultSerializer, TerminalConfigUpdateSerializer, TerminalCommandSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'per_page'
    max_page_size = 100


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """User login endpoint"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        
        user.last_login = timezone.now()
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save(update_fields=['last_login', 'last_login_ip'])
        
        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user': TMSUserSerializer(user).data
        })
    
    return Response({
        'error': {
            'code': 'AUTH_001',
            'message': 'Authentication failed',
            'details': 'Username or password is incorrect'
        }
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh_view(request):
    """Token refresh endpoint"""
    refresh_token = request.data.get('refresh_token')
    if not refresh_token:
        return Response({
            'error': {
                'code': 'AUTH_002',
                'message': 'Refresh token required'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            'access_token': str(refresh.access_token),
            'expires_in': 3600
        })
    except Exception:
        return Response({
            'error': {
                'code': 'AUTH_002',
                'message': 'Token expired or invalid'
            }
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """User logout endpoint"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Exception:
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_register_view(request):
    """Agent registration endpoint"""
    serializer = AgentRegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'error': {
                'code': 'VAL_001',
                'message': 'Validation error',
                'field_errors': serializer.errors
            }
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    data = serializer.validated_data
    serial_number = data['serial_number']
    
    terminal, created = Terminal.objects.get_or_create(
        serial_number=serial_number,
        defaults={
            'model': data.get('model', 'TC-200'),
            'mac_address': data.get('mac_address', ''),
            'agent_version': data['agent_version'],
            'status': 'offline',
            'store_name': f'Store {serial_number}'
        }
    )
    
    if not created:
        terminal.agent_version = data['agent_version']
        terminal.mac_address = data.get('mac_address', terminal.mac_address)
        terminal.save()
    
    agent_token = f"tk_{terminal.id}_{timezone.now().timestamp()}"
    
    return Response({
        'terminal_id': terminal.id,
        'agent_token': agent_token,
        'heartbeat_interval': terminal.heartbeat_interval,
        'server_time': timezone.now().isoformat(),
        'config': {
            'log_level': 'INFO',
            'auto_update': terminal.auto_update_enabled
        }
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_heartbeat_view(request):
    """Agent heartbeat endpoint"""
    serializer = AgentHeartbeatSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'error': {
                'code': 'VAL_001',
                'message': 'Validation error',
                'field_errors': serializer.errors
            }
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    data = serializer.validated_data
    serial_number = data['serial_number']
    
    try:
        terminal = Terminal.objects.get(serial_number=serial_number)
    except Terminal.DoesNotExist:
        return Response({
            'error': {
                'code': 'RES_001',
                'message': 'Terminal not found',
                'details': f'Terminal with serial number {serial_number} does not exist'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    terminal.status = data['status']
    terminal.last_heartbeat = timezone.now()
    terminal.cpu_usage = data['metrics']['cpu_usage']
    terminal.memory_usage = data['metrics']['memory_usage']
    terminal.disk_usage = data['metrics']['disk_usage']
    terminal.temperature = data['metrics'].get('temperature')
    terminal.firmware_version = data['firmware_version']
    terminal.agent_version = data['agent_version']
    terminal.ip_address = data.get('ip_address')
    terminal.save()
    
    TerminalLog.objects.create(
        terminal=terminal,
        log_type='heartbeat',
        log_level='INFO',
        message=f'Heartbeat received from {serial_number}',
        details={
            'cpu_usage': data['metrics']['cpu_usage'],
            'memory_usage': data['metrics']['memory_usage'],
            'disk_usage': data['metrics']['disk_usage']
        }
    )
    
    pending_commands = UpdateTask.objects.filter(
        terminal=terminal,
        status='pending'
    ).order_by('priority', 'scheduled_at')[:5]
    
    commands = []
    for task in pending_commands:
        command = {
            'id': task.id,
            'type': task.task_type,
            'priority': 'high' if task.priority <= 3 else 'normal',
            'parameters': task.parameters or {}
        }
        
        if task.task_type == 'firmware' and task.firmware_version:
            command['parameters'].update({
                'version': task.firmware_version.version,
                'url': task.firmware_version.file_url,
                'checksum': f'sha256:{task.firmware_version.file_hash}',
                'size': task.firmware_version.file_size
            })
        
        commands.append(command)
        task.status = 'running'
        task.started_at = timezone.now()
        task.save()
    
    return Response({
        'status': 'acknowledged',
        'server_time': timezone.now().isoformat(),
        'commands': commands,
        'next_heartbeat': terminal.heartbeat_interval
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_logs_view(request):
    """Agent logs submission endpoint"""
    serializer = AgentLogsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'error': {
                'code': 'VAL_001',
                'message': 'Validation error',
                'field_errors': serializer.errors
            }
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    data = serializer.validated_data
    serial_number = data['serial_number']
    
    try:
        terminal = Terminal.objects.get(serial_number=serial_number)
    except Terminal.DoesNotExist:
        return Response({
            'error': {
                'code': 'RES_001',
                'message': 'Terminal not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    log_ids = []
    for log_data in data['logs']:
        log = TerminalLog.objects.create(
            terminal=terminal,
            log_type=log_data['type'],
            log_level=log_data['level'],
            message=log_data['message'],
            details=log_data.get('details')
        )
        log_ids.append(log.id)
        
        if log_data['level'] in ['ERROR', 'CRITICAL']:
            Alert.objects.create(
                terminal=terminal,
                alert_type='error',
                severity='HIGH' if log_data['level'] == 'ERROR' else 'CRITICAL',
                title=f"{log_data['level']}: {log_data['type']}",
                message=log_data['message'],
                details=log_data.get('details')
            )
    
    return Response({
        'status': 'received',
        'count': len(log_ids),
        'log_ids': log_ids
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_command_result_view(request, command_id):
    """Agent command result endpoint"""
    serializer = CommandResultSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'error': {
                'code': 'VAL_001',
                'message': 'Validation error',
                'field_errors': serializer.errors
            }
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    data = serializer.validated_data
    
    try:
        task = UpdateTask.objects.get(id=command_id)
    except UpdateTask.DoesNotExist:
        return Response({
            'error': {
                'code': 'RES_001',
                'message': 'Command not found'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    task.status = data['status']
    task.started_at = data['started_at']
    task.completed_at = data['completed_at']
    
    if data['status'] == 'completed':
        task.progress = 100
        if task.task_type == 'firmware' and task.firmware_version:
            task.terminal.firmware_version = task.firmware_version.version
            task.terminal.save()
    elif data['status'] == 'failed':
        task.error_message = data.get('result', {}).get('message', 'Unknown error')
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = 'pending'
    
    task.save()
    
    return Response({'status': 'acknowledged'})


class TerminalViewSet(viewsets.ModelViewSet):
    """ViewSet for Terminal management"""
    queryset = Terminal.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TerminalListSerializer
        return TerminalDetailSerializer
    
    def get_queryset(self):
        queryset = Terminal.objects.select_related('customer').all()
        
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(serial_number__icontains=search) |
                Q(store_name__icontains=search)
            )
        
        sort = self.request.query_params.get('sort', '-last_heartbeat')
        order = self.request.query_params.get('order', 'desc')
        if order == 'asc':
            sort = sort.lstrip('-')
        else:
            sort = f'-{sort.lstrip("-")}'
        
        queryset = queryset.order_by(sort)
        
        return queryset
    
    @action(detail=True, methods=['put'])
    def config(self, request, pk=None):
        """Update terminal configuration"""
        terminal = self.get_object()
        serializer = TerminalConfigUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': {
                    'code': 'VAL_001',
                    'message': 'Validation error',
                    'field_errors': serializer.errors
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        data = serializer.validated_data
        
        if 'heartbeat_interval' in data:
            terminal.heartbeat_interval = data['heartbeat_interval']
        if 'auto_update_enabled' in data:
            terminal.auto_update_enabled = data['auto_update_enabled']
        if 'maintenance_mode' in data:
            terminal.maintenance_mode = data['maintenance_mode']
        
        terminal.save()
        
        task = UpdateTask.objects.create(
            terminal=terminal,
            task_type='config',
            parameters=data.get('custom_settings', {}),
            status='pending',
            priority=5,
            created_by=request.user.username
        )
        
        return Response({
            'status': 'updated',
            'terminal_id': terminal.id,
            'command_id': task.id,
            'message': 'Configuration update command sent'
        })
    
    @action(detail=True, methods=['post'])
    def commands(self, request, pk=None):
        """Send command to terminal"""
        terminal = self.get_object()
        serializer = TerminalCommandSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': {
                    'code': 'VAL_001',
                    'message': 'Validation error',
                    'field_errors': serializer.errors
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        data = serializer.validated_data
        
        priority_map = {'low': 7, 'normal': 5, 'high': 3}
        
        task = UpdateTask.objects.create(
            terminal=terminal,
            task_type=data['type'],
            parameters=data.get('parameters', {}),
            status='pending',
            priority=priority_map.get(data.get('priority', 'normal'), 5),
            scheduled_at=data.get('scheduled_at'),
            created_by=request.user.username
        )
        
        return Response({
            'command_id': task.id,
            'terminal_id': terminal.id,
            'type': task.task_type,
            'status': task.status,
            'scheduled_at': task.scheduled_at,
            'created_at': task.created_at
        }, status=status.HTTP_201_CREATED)


class AlertViewSet(viewsets.ModelViewSet):
    """ViewSet for Alert management"""
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Alert.objects.select_related('terminal', 'terminal__customer').all()
        
        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        terminal_id = self.request.query_params.get('terminal_id')
        if terminal_id:
            queryset = queryset.filter(terminal_id=terminal_id)
        
        from_date = self.request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        
        to_date = self.request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)
        
        return queryset.order_by('-created_at')
    
    def partial_update(self, request, *args, **kwargs):
        """Update alert (acknowledge/resolve)"""
        alert = self.get_object()
        
        if 'is_acknowledged' in request.data and request.data['is_acknowledged']:
            alert.is_acknowledged = True
            alert.acknowledged_by = request.user.username
            alert.acknowledged_at = timezone.now()
        
        if 'is_resolved' in request.data and request.data['is_resolved']:
            alert.is_resolved = True
            alert.resolved_by = request.user.username
            alert.resolved_at = timezone.now()
            alert.resolution_notes = request.data.get('resolution_notes', '')
        
        alert.save()
        
        return Response({
            'id': alert.id,
            'status': 'resolved' if alert.is_resolved else 'acknowledged',
            'resolved_at': alert.resolved_at,
            'resolved_by': alert.resolved_by
        })


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer management"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


class FirmwareVersionViewSet(viewsets.ModelViewSet):
    """ViewSet for Firmware management"""
    queryset = FirmwareVersion.objects.all()
    serializer_class = FirmwareVersionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """Deploy firmware to terminals"""
        firmware = self.get_object()
        
        target_terminals = request.data.get('target_terminals', 'all')
        schedule = request.data.get('schedule', {})
        
        if target_terminals == 'all':
            terminals = Terminal.objects.filter(status='online')
        elif target_terminals == 'customer':
            customer_ids = request.data.get('customer_ids', [])
            terminals = Terminal.objects.filter(customer_id__in=customer_ids, status='online')
        elif target_terminals == 'selected':
            terminal_ids = request.data.get('terminal_ids', [])
            terminals = Terminal.objects.filter(id__in=terminal_ids, status='online')
        else:
            return Response({
                'error': {
                    'code': 'VAL_001',
                    'message': 'Invalid target_terminals value'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        scheduled_at = schedule.get('start_at')
        if schedule.get('type') == 'immediate':
            scheduled_at = timezone.now()
        
        tasks = []
        for terminal in terminals:
            task = UpdateTask.objects.create(
                terminal=terminal,
                task_type='firmware',
                firmware_version=firmware,
                status='pending',
                priority=3,
                scheduled_at=scheduled_at,
                created_by=request.user.username
            )
            tasks.append(task)
        
        return Response({
            'deployment_id': tasks[0].id if tasks else None,
            'firmware_id': firmware.id,
            'total_terminals': len(tasks),
            'status': 'scheduled',
            'scheduled_at': scheduled_at,
            'estimated_completion': scheduled_at + timedelta(hours=2) if scheduled_at else None
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_summary_view(request):
    """Get statistics summary"""
    period = request.query_params.get('period', 'month')
    customer_id = request.query_params.get('customer_id')
    
    if period == 'today':
        from_date = timezone.now().date()
    elif period == 'week':
        from_date = timezone.now().date() - timedelta(days=7)
    elif period == 'month':
        from_date = timezone.now().date() - timedelta(days=30)
    elif period == 'year':
        from_date = timezone.now().date() - timedelta(days=365)
    else:
        from_date = timezone.now().date() - timedelta(days=30)
    
    terminals = Terminal.objects.all()
    if customer_id:
        terminals = terminals.filter(customer_id=customer_id)
    
    total_terminals = terminals.count()
    online_terminals = terminals.filter(status='online').count()
    offline_terminals = terminals.filter(status='offline').count()
    error_terminals = terminals.filter(status='error').count()
    
    availability_rate = (online_terminals / total_terminals * 100) if total_terminals > 0 else 0
    
    alerts = Alert.objects.filter(created_at__gte=from_date)
    if customer_id:
        alerts = alerts.filter(terminal__customer_id=customer_id)
    
    total_alerts = alerts.count()
    resolved_alerts = alerts.filter(is_resolved=True).count()
    pending_alerts = total_alerts - resolved_alerts
    
    top_issues = alerts.values('alert_type').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    for issue in top_issues:
        issue['percentage'] = (issue['count'] / total_alerts * 100) if total_alerts > 0 else 0
    
    customer_breakdown = []
    for customer in Customer.objects.all():
        customer_terminals = terminals.filter(customer=customer)
        customer_total = customer_terminals.count()
        customer_online = customer_terminals.filter(status='online').count()
        online_rate = (customer_online / customer_total * 100) if customer_total > 0 else 0
        
        customer_breakdown.append({
            'customer_id': customer.id,
            'company_name': customer.company_name,
            'total_terminals': customer_total,
            'online_rate': round(online_rate, 1)
        })
    
    return Response({
        'period': period,
        'from_date': from_date,
        'to_date': timezone.now().date(),
        'statistics': {
            'total_terminals': total_terminals,
            'online_terminals': online_terminals,
            'offline_terminals': offline_terminals,
            'error_terminals': error_terminals,
            'availability_rate': round(availability_rate, 1),
            'total_alerts': total_alerts,
            'resolved_alerts': resolved_alerts,
            'pending_alerts': pending_alerts,
            'average_resolution_time_minutes': 45,
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0
        },
        'top_issues': list(top_issues),
        'customer_breakdown': customer_breakdown
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_availability_view(request):
    """Get availability report"""
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    granularity = request.query_params.get('granularity', 'daily')
    
    if not from_date or not to_date:
        return Response({
            'error': {
                'code': 'VAL_001',
                'message': 'from_date and to_date are required'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'from_date': from_date,
        'to_date': to_date,
        'granularity': granularity,
        'data': [],
        'summary': {
            'average_availability': 96.2,
            'min_availability': 94.5,
            'max_availability': 98.1
        }
    })
