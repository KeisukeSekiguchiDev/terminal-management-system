from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Terminal, Customer, Alert, FirmwareVersion, TMSUser, TerminalLog
import json


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'terminals/login.html', {'error': 'Invalid username or password'})
    
    return render(request, 'terminals/login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    total_terminals = Terminal.objects.count()
    online_terminals = Terminal.objects.filter(status='online').count()
    offline_terminals = Terminal.objects.filter(status='offline').count()
    error_terminals = Terminal.objects.filter(status='error').count()
    
    online_percentage = round((online_terminals / total_terminals * 100) if total_terminals > 0 else 0, 1)
    offline_percentage = round((offline_terminals / total_terminals * 100) if total_terminals > 0 else 0, 1)
    error_percentage = round((error_terminals / total_terminals * 100) if total_terminals > 0 else 0, 1)
    
    recent_alerts = Alert.objects.filter(is_resolved=False).select_related('terminal').order_by('-created_at')[:5]
    
    customer_stats = []
    for customer in Customer.objects.all()[:5]:
        terminals = Terminal.objects.filter(customer=customer)
        total = terminals.count()
        online = terminals.filter(status='online').count()
        availability_rate = round((online / total * 100) if total > 0 else 0, 1)
        
        if availability_rate >= 99:
            availability_class = 'success'
        elif availability_rate >= 95:
            availability_class = 'warning'
        else:
            availability_class = 'danger'
        
        customer_stats.append({
            'id': customer.id,
            'company_name': customer.company_name,
            'total_terminals': total,
            'online_terminals': online,
            'availability_rate': availability_rate,
            'availability_class': availability_class
        })
    
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        chart_labels.append(date.strftime('%m/%d'))
        chart_data.append(95 + (i % 3))
    
    context = {
        'total_terminals': total_terminals,
        'online_terminals': online_terminals,
        'offline_terminals': offline_terminals,
        'error_terminals': error_terminals,
        'online_percentage': online_percentage,
        'offline_percentage': offline_percentage,
        'error_percentage': error_percentage,
        'recent_alerts': recent_alerts,
        'customer_stats': customer_stats,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'last_update': timezone.now().strftime('%H:%M:%S'),
    }
    
    return render(request, 'terminals/dashboard.html', context)


@login_required
def terminal_list_view(request):
    terminals = Terminal.objects.select_related('customer').all()
    
    search = request.GET.get('search')
    if search:
        terminals = terminals.filter(
            Q(serial_number__icontains=search) | Q(store_name__icontains=search)
        )
    
    customer_id = request.GET.get('customer_id')
    if customer_id:
        terminals = terminals.filter(customer_id=customer_id)
    
    status = request.GET.get('status')
    if status:
        terminals = terminals.filter(status=status)
    
    terminals = terminals.order_by('-last_heartbeat')
    
    paginator = Paginator(terminals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    customers = Customer.objects.all()
    
    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'customers': customers,
    }
    
    return render(request, 'terminals/terminal_list.html', context)


@login_required
def terminal_detail_view(request, terminal_id):
    terminal = get_object_or_404(Terminal.objects.select_related('customer'), id=terminal_id)
    recent_logs = TerminalLog.objects.filter(terminal=terminal).order_by('-created_at')[:10]
    active_alerts = Alert.objects.filter(terminal=terminal, is_resolved=False).order_by('-created_at')
    
    context = {
        'terminal': terminal,
        'recent_logs': recent_logs,
        'active_alerts': active_alerts,
    }
    
    return render(request, 'terminals/terminal_detail.html', context)


@login_required
def terminal_new_view(request):
    if request.method == 'POST':
        pass
    
    customers = Customer.objects.all()
    return render(request, 'terminals/terminal_new.html', {'customers': customers})


@login_required
def alert_list_view(request):
    alerts = Alert.objects.select_related('terminal').all()
    
    severity = request.GET.get('severity')
    if severity:
        alerts = alerts.filter(severity=severity)
    
    status = request.GET.get('status')
    if status == 'unresolved':
        alerts = alerts.filter(is_resolved=False)
    elif status == 'acknowledged':
        alerts = alerts.filter(is_acknowledged=True, is_resolved=False)
    elif status == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    
    terminal = request.GET.get('terminal')
    if terminal:
        alerts = alerts.filter(terminal__serial_number__icontains=terminal)
    
    alerts = alerts.order_by('-created_at')
    
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'paginator': paginator,
    }
    
    return render(request, 'terminals/alert_list.html', context)


@login_required
def customer_list_view(request):
    customers = Customer.objects.annotate(
        terminal_count=Count('terminal')
    ).all()
    
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'paginator': paginator,
    }
    
    return render(request, 'terminals/customer_list.html', context)


@login_required
def customer_detail_view(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    terminals = Terminal.objects.filter(customer=customer).order_by('-last_heartbeat')[:10]
    
    all_terminals = Terminal.objects.filter(customer=customer)
    terminal_stats = {
        'total': all_terminals.count(),
        'online': all_terminals.filter(status='online').count(),
        'offline': all_terminals.filter(status='offline').count(),
        'error': all_terminals.filter(status='error').count(),
    }
    
    context = {
        'customer': customer,
        'terminals': terminals,
        'terminal_stats': terminal_stats,
    }
    
    return render(request, 'terminals/customer_detail.html', context)


@login_required
def customer_new_view(request):
    if request.method == 'POST':
        pass
    
    return render(request, 'terminals/customer_new.html')


@login_required
def firmware_list_view(request):
    firmwares = FirmwareVersion.objects.annotate(
        deployed_count=Count('updatetask')
    ).order_by('-release_date')
    
    customers = Customer.objects.all()
    
    context = {
        'firmwares': firmwares,
        'customers': customers,
    }
    
    return render(request, 'terminals/firmware_list.html', context)


@login_required
def firmware_upload_view(request):
    if request.method == 'POST':
        pass
    
    return redirect('firmware_list')


@login_required
def reports_view(request):
    total_terminals = Terminal.objects.count()
    online_terminals = Terminal.objects.filter(status='online').count()
    total_alerts = Alert.objects.filter(is_resolved=False).count()
    total_customers = Customer.objects.count()
    
    online_percentage = round((online_terminals / total_terminals * 100) if total_terminals > 0 else 0, 1)
    
    summary = {
        'total_terminals': total_terminals,
        'online_terminals': online_terminals,
        'total_alerts': total_alerts,
        'total_customers': total_customers,
        'online_percentage': online_percentage,
    }
    
    availability_by_customer = []
    for customer in Customer.objects.all():
        terminals = Terminal.objects.filter(customer=customer)
        total = terminals.count()
        online = terminals.filter(status='online').count()
        availability = round((online / total * 100) if total > 0 else 0, 1)
        
        availability_by_customer.append({
            'customer_name': customer.company_name,
            'terminal_count': total,
            'availability': availability,
        })
    
    alert_counts = Alert.objects.values('severity').annotate(count=Count('id'))
    alert_labels = [item['severity'] for item in alert_counts]
    alert_data = [item['count'] for item in alert_counts]
    
    firmware_distribution = []
    firmware_counts = Terminal.objects.values('firmware_version').annotate(count=Count('id'))
    for item in firmware_counts:
        percentage = round((item['count'] / total_terminals * 100) if total_terminals > 0 else 0, 1)
        firmware_distribution.append({
            'version': item['firmware_version'] or 'Unknown',
            'count': item['count'],
            'percentage': percentage,
        })
    
    context = {
        'summary': summary,
        'availability_by_customer': availability_by_customer,
        'alert_labels': json.dumps(alert_labels),
        'alert_data': json.dumps(alert_data),
        'firmware_distribution': firmware_distribution,
    }
    
    return render(request, 'terminals/reports.html', context)
