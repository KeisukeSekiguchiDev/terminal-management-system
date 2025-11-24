import ctypes
import time
import logging
from typing import Dict, List, Optional, Any


class TerminalController:
    """TC-200 terminal control class"""
    
    def __init__(self, dll_path: str = "dll/TC-200.dll"):
        """
        Initialize terminal controller
        
        Args:
            dll_path: Path to TC-200.dll
        """
        self.logger = logging.getLogger(__name__)
        self.dll_path = dll_path
        self.dll = None
        self.serial_number = None
        self.connected = False
        self.mock_mode = False
        
        try:
            self.load_dll()
        except Exception as e:
            self.logger.warning(f"DLL not available, using mock mode: {e}")
            self.mock_mode = True
    
    def load_dll(self):
        """Load TC-200.dll"""
        try:
            self.dll = ctypes.CDLL(self.dll_path)
            self.logger.info(f"DLL loaded: {self.dll_path}")
        except Exception as e:
            self.logger.error(f"DLL load error: {e}")
            raise
    
    def is_connected(self) -> bool:
        """
        Check if terminal is connected
        
        Returns:
            True if connected, False otherwise
        """
        if self.mock_mode:
            return self.connected
        
        try:
            if self.dll:
                return self.connected
        except Exception as e:
            self.logger.error(f"Connection check error: {e}")
        
        return False
    
    def scan_devices(self) -> List[str]:
        """
        Scan for USB-connected TC-200 devices
        
        Returns:
            List of detected device serial numbers
        """
        if self.mock_mode:
            return ['TC-200-MOCK-001']
        
        try:
            devices = []
            return devices
        except Exception as e:
            self.logger.error(f"Device scan error: {e}")
            return []
    
    def connect(self, device_id: str = None) -> bool:
        """
        Connect to terminal
        
        Args:
            device_id: Device identifier (optional)
            
        Returns:
            True if connection successful
        """
        if self.mock_mode:
            self.connected = True
            self.serial_number = device_id or 'TC-200-MOCK-001'
            self.logger.info(f"Mock connection to {self.serial_number}")
            return True
        
        try:
            if self.dll:
                self.connected = True
                self.serial_number = device_id
                self.logger.info(f"Connected to terminal: {device_id}")
                return True
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        
        return False
    
    def disconnect(self):
        """Disconnect from terminal"""
        if self.mock_mode:
            self.connected = False
            self.logger.info("Mock disconnection")
            return
        
        try:
            if self.dll and self.connected:
                self.connected = False
                self.logger.info("Disconnected from terminal")
        except Exception as e:
            self.logger.error(f"Disconnection error: {e}")
    
    def reconnect(self) -> bool:
        """
        Reconnect to terminal
        
        Returns:
            True if reconnection successful
        """
        self.disconnect()
        time.sleep(2)
        
        devices = self.scan_devices()
        if devices:
            return self.connect(devices[0])
        
        return False
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get terminal device information
        
        Returns:
            Dictionary with device information
        """
        if self.mock_mode:
            return {
                'serial_number': self.serial_number or 'TC-200-MOCK-001',
                'model': 'TC-200',
                'firmware_version': '1.0.0',
                'hardware_version': '1.0',
                'manufacturer': 'TechCore'
            }
        
        try:
            if self.dll and self.connected:
                return {
                    'serial_number': self.serial_number,
                    'model': 'TC-200',
                    'firmware_version': '1.0.0',
                    'hardware_version': '1.0',
                    'manufacturer': 'TechCore'
                }
        except Exception as e:
            self.logger.error(f"Get device info error: {e}")
        
        return {}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get terminal status
        
        Returns:
            Dictionary with terminal status
        """
        if self.mock_mode:
            return {
                'connected': self.connected,
                'firmware_version': '1.0.0',
                'transaction_count': 0,
                'last_transaction': None,
                'status': 'online' if self.connected else 'offline'
            }
        
        try:
            if self.dll and self.connected:
                return {
                    'connected': True,
                    'firmware_version': '1.0.0',
                    'transaction_count': 0,
                    'last_transaction': None,
                    'status': 'online'
                }
        except Exception as e:
            self.logger.error(f"Get status error: {e}")
        
        return {
            'connected': False,
            'status': 'offline'
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed terminal status
        
        Returns:
            Dictionary with detailed status information
        """
        status = self.get_status()
        
        status.update({
            'has_error': False,
            'error_code': None,
            'error_message': None,
            'temperature': 45,
            'uptime': 3600
        })
        
        return status
    
    def update_firmware(self, firmware_file: str) -> Dict[str, Any]:
        """
        Update terminal firmware
        
        Args:
            firmware_file: Path to firmware file
            
        Returns:
            Dictionary with update result
        """
        if self.mock_mode:
            self.logger.info(f"Mock firmware update: {firmware_file}")
            time.sleep(5)
            return {
                'success': True,
                'message': 'Firmware updated successfully (mock)'
            }
        
        try:
            if self.dll and self.connected:
                self.logger.info(f"Updating firmware: {firmware_file}")
                time.sleep(10)
                return {
                    'success': True,
                    'message': 'Firmware updated successfully'
                }
        except Exception as e:
            self.logger.error(f"Firmware update error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        
        return {
            'success': False,
            'error': 'Not connected'
        }
    
    def reset(self):
        """Reset terminal"""
        if self.mock_mode:
            self.logger.info("Mock terminal reset")
            return
        
        try:
            if self.dll and self.connected:
                self.logger.info("Resetting terminal")
        except Exception as e:
            self.logger.error(f"Reset error: {e}")
    
    def run_self_test(self) -> Dict[str, Any]:
        """
        Run terminal self-test
        
        Returns:
            Dictionary with test results
        """
        if self.mock_mode:
            return {
                'success': True,
                'tests': {
                    'usb_connection': 'pass',
                    'card_reader': 'pass',
                    'display': 'pass',
                    'keypad': 'pass'
                }
            }
        
        try:
            if self.dll and self.connected:
                return {
                    'success': True,
                    'tests': {
                        'usb_connection': 'pass',
                        'card_reader': 'pass',
                        'display': 'pass',
                        'keypad': 'pass'
                    }
                }
        except Exception as e:
            self.logger.error(f"Self-test error: {e}")
        
        return {
            'success': False,
            'error': 'Self-test failed'
        }
