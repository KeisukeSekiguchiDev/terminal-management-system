from django.urls import path
from . import web_views

urlpatterns = [
    path('login', web_views.login_view, name='login'),
    path('logout', web_views.logout_view, name='logout'),
    path('dashboard', web_views.dashboard_view, name='dashboard'),
    
    path('terminals', web_views.terminal_list_view, name='terminal_list'),
    path('terminals/new', web_views.terminal_new_view, name='terminal_new'),
    path('terminals/<int:terminal_id>', web_views.terminal_detail_view, name='terminal_detail'),
    
    path('alerts', web_views.alert_list_view, name='alert_list'),
    
    path('customers', web_views.customer_list_view, name='customer_list'),
    path('customers/new', web_views.customer_new_view, name='customer_new'),
    path('customers/<int:customer_id>', web_views.customer_detail_view, name='customer_detail'),
    
    path('firmware', web_views.firmware_list_view, name='firmware_list'),
    path('firmware/upload', web_views.firmware_upload_view, name='firmware_upload'),
    
    path('reports', web_views.reports_view, name='reports'),
]
