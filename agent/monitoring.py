import psutil
import platform
import socket
import logging
from typing import Dict, Any


class SystemMonitor:
    """System monitoring class"""
    
    def __init__(self):
        """Initialize system monitor"""
        self.logger = logging.getLogger(__name__)
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information
        
        Returns:
            Dictionary with system information
        """
        try:
            return {
                'hostname': socket.gethostname(),
                'os_version': platform.platform(),
                'os_name': platform.system(),
                'os_release': platform.release(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'ip_address': self.get_ip_address()
            }
        except Exception as e:
            self.logger.error(f"Get system info error: {e}")
            return {}
    
    def get_ip_address(self) -> str:
        """
        Get local IP address
        
        Returns:
            IP address string
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics
        
        Returns:
            Dictionary with system metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage': int(cpu_percent),
                'memory_usage': int(memory.percent),
                'disk_usage': int(disk.percent),
                'memory_total': memory.total,
                'memory_available': memory.available,
                'disk_total': disk.total,
                'disk_free': disk.free,
                'uptime': int(psutil.boot_time())
            }
        except Exception as e:
            self.logger.error(f"Get metrics error: {e}")
            return {
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0,
                'uptime': 0
            }
    
    def run_system_check(self) -> Dict[str, Any]:
        """
        Run system health check
        
        Returns:
            Dictionary with check results
        """
        try:
            metrics = self.get_metrics()
            
            checks = {
                'cpu_ok': metrics['cpu_usage'] < 90,
                'memory_ok': metrics['memory_usage'] < 90,
                'disk_ok': metrics['disk_usage'] < 90,
                'network_ok': self.check_network_connectivity()
            }
            
            checks['overall_ok'] = all(checks.values())
            
            return checks
        except Exception as e:
            self.logger.error(f"System check error: {e}")
            return {
                'overall_ok': False,
                'error': str(e)
            }
    
    def check_network_connectivity(self) -> bool:
        """
        Check network connectivity
        
        Returns:
            True if network is available
        """
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception:
            return False
