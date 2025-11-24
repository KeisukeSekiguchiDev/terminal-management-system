from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'terminals', views.TerminalViewSet, basename='terminal')
router.register(r'alerts', views.AlertViewSet, basename='alert')
router.register(r'customers', views.CustomerViewSet, basename='customer')
router.register(r'firmware', views.FirmwareVersionViewSet, basename='firmware')

urlpatterns = [
    path('auth/login', views.login_view, name='login'),
    path('auth/refresh', views.token_refresh_view, name='token-refresh'),
    path('auth/logout', views.logout_view, name='logout'),
    
    path('agent/register', views.agent_register_view, name='agent-register'),
    path('agent/heartbeat', views.agent_heartbeat_view, name='agent-heartbeat'),
    path('agent/logs', views.agent_logs_view, name='agent-logs'),
    path('agent/commands/<int:command_id>/result', views.agent_command_result_view, name='agent-command-result'),
    
    path('reports/summary', views.reports_summary_view, name='reports-summary'),
    path('reports/availability', views.reports_availability_view, name='reports-availability'),
    
    path('', include(router.urls)),
]
