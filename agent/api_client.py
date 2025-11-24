import requests
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime


class APIClient:
    """TMS Server API client"""
    
    def __init__(self, server_url: str, api_key: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            server_url: TMS server URL
            api_key: API authentication key
        """
        self.logger = logging.getLogger(__name__)
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TMS-Agent/1.0.0'
        })
        
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
    
    def set_api_key(self, api_key: str):
        """
        Set API authentication key
        
        Args:
            api_key: API key
        """
        self.api_key = api_key
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}'
        })
    
    def register(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register agent with server
        
        Args:
            registration_data: Registration information
            
        Returns:
            Registration response
        """
        try:
            url = f'{self.server_url}/agent/register'
            response = self.session.post(url, json=registration_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info("Agent registration successful")
                
                if 'agent_token' in data:
                    self.set_api_key(data['agent_token'])
                
                return {
                    'status': 'success',
                    'token': data.get('agent_token'),
                    'terminal_id': data.get('terminal_id')
                }
            else:
                self.logger.error(f"Registration failed: {response.status_code}")
                return {
                    'status': 'error',
                    'message': response.text
                }
        
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def send_heartbeat(self, heartbeat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send heartbeat to server
        
        Args:
            heartbeat_data: Heartbeat information
            
        Returns:
            Server response with commands
        """
        try:
            url = f'{self.server_url}/agent/heartbeat'
            response = self.session.post(url, json=heartbeat_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.debug("Heartbeat sent successfully")
                return data
            else:
                self.logger.warning(f"Heartbeat failed: {response.status_code}")
                return {}
        
        except Exception as e:
            self.logger.error(f"Heartbeat error: {e}")
            return {}
    
    def send_logs(self, logs: list) -> bool:
        """
        Send logs to server
        
        Args:
            logs: List of log entries
            
        Returns:
            True if successful
        """
        try:
            url = f'{self.server_url}/agent/logs'
            response = self.session.post(url, json={'logs': logs}, timeout=30)
            
            if response.status_code == 200:
                self.logger.debug("Logs sent successfully")
                return True
            else:
                self.logger.warning(f"Log transmission failed: {response.status_code}")
                return False
        
        except Exception as e:
            self.logger.error(f"Log transmission error: {e}")
            return False
    
    def send_command_result(self, result: Dict[str, Any]) -> bool:
        """
        Send command execution result
        
        Args:
            result: Command result
            
        Returns:
            True if successful
        """
        try:
            command_id = result.get('command_id')
            url = f'{self.server_url}/agent/commands/{command_id}/result'
            response = self.session.post(url, json=result, timeout=30)
            
            if response.status_code == 200:
                self.logger.debug(f"Command result sent: {command_id}")
                return True
            else:
                self.logger.warning(f"Command result failed: {response.status_code}")
                return False
        
        except Exception as e:
            self.logger.error(f"Command result error: {e}")
            return False
    
    def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert to server
        
        Args:
            alert_data: Alert information
            
        Returns:
            True if successful
        """
        try:
            log_entry = {
                'log_type': 'alert',
                'log_level': 'ERROR',
                'message': alert_data.get('message', 'Alert'),
                'details': alert_data,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.send_logs([log_entry])
        
        except Exception as e:
            self.logger.error(f"Alert transmission error: {e}")
            return False
    
    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Send event to server
        
        Args:
            event_data: Event information
            
        Returns:
            True if successful
        """
        try:
            log_entry = {
                'log_type': 'event',
                'log_level': 'INFO',
                'message': event_data.get('type', 'Event'),
                'details': event_data,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.send_logs([log_entry])
        
        except Exception as e:
            self.logger.error(f"Event transmission error: {e}")
            return False
    
    def download_firmware(self, download_url: str, save_path: str) -> str:
        """
        Download firmware file
        
        Args:
            download_url: Firmware download URL
            save_path: Path to save firmware
            
        Returns:
            Path to downloaded file
        """
        try:
            self.logger.info(f"Downloading firmware from {download_url}")
            
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"Firmware downloaded: {save_path}")
            return save_path
        
        except Exception as e:
            self.logger.error(f"Firmware download error: {e}")
            raise
    
    def check_firmware_update(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """
        Check for firmware updates
        
        Args:
            serial_number: Terminal serial number
            
        Returns:
            Update information if available
        """
        try:
            url = f'{self.server_url}/terminals/{serial_number}/firmware-update'
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('update_available'):
                    return data
            
            return None
        
        except Exception as e:
            self.logger.error(f"Firmware update check error: {e}")
            return None
    
    def send_update_result(self, result: Dict[str, Any]) -> bool:
        """
        Send firmware update result
        
        Args:
            result: Update result
            
        Returns:
            True if successful
        """
        try:
            log_entry = {
                'log_type': 'firmware_update',
                'log_level': 'INFO' if result.get('status') == 'success' else 'ERROR',
                'message': f"Firmware update {result.get('status')}",
                'details': result,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.send_logs([log_entry])
        
        except Exception as e:
            self.logger.error(f"Update result error: {e}")
            return False
    
    def send_diagnostics(self, diagnostics: Dict[str, Any]) -> bool:
        """
        Send diagnostic results
        
        Args:
            diagnostics: Diagnostic information
            
        Returns:
            True if successful
        """
        try:
            log_entry = {
                'log_type': 'diagnostics',
                'log_level': 'INFO',
                'message': 'Diagnostic results',
                'details': diagnostics,
                'timestamp': datetime.now().isoformat()
            }
            
            return self.send_logs([log_entry])
        
        except Exception as e:
            self.logger.error(f"Diagnostics transmission error: {e}")
            return False
    
    def upload_logs(self, archive_path: str) -> bool:
        """
        Upload log archive
        
        Args:
            archive_path: Path to log archive
            
        Returns:
            True if successful
        """
        try:
            url = f'{self.server_url}/agent/logs/upload'
            
            with open(archive_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(url, files=files, timeout=300)
            
            if response.status_code == 200:
                self.logger.info("Log archive uploaded successfully")
                return True
            else:
                self.logger.warning(f"Log upload failed: {response.status_code}")
                return False
        
        except Exception as e:
            self.logger.error(f"Log upload error: {e}")
            return False
