import logging
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    """Audit logging middleware"""
    
    def process_request(self, request):
        """Store request start time"""
        request._audit_start_time = timezone.now()
        return None
    
    def process_response(self, request, response):
        """Log request/response"""
        if not hasattr(request, '_audit_start_time'):
            return response
        
        if request.path.startswith('/api/') or request.path.startswith('/admin/'):
            try:
                user = request.user if request.user.is_authenticated else None
                
                ip_address = self.get_client_ip(request)
                
                AuditLog.objects.create(
                    user=user,
                    action=f"{request.method} {request.path}",
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    request_data=self.get_request_data(request),
                    response_status=response.status_code,
                    timestamp=request._audit_start_time
                )
            except Exception as e:
                logger.error(f"Audit logging error: {e}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_request_data(self, request):
        """Get request data (sanitized)"""
        try:
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.POST.dict() if request.POST else {}
                
                if 'password' in data:
                    data['password'] = '***'
                if 'token' in data:
                    data['token'] = '***'
                
                return str(data)[:1000]
        except Exception:
            pass
        
        return ""


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Security headers middleware"""
    
    def process_response(self, request, response):
        """Add security headers"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
