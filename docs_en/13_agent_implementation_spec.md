# Agent Implementation Specification
## Store PC TMS Agent

**Document Version**: 1.0
**Created Date**: November 24, 2025
**Target Terminal**: TC-200 (USB-connected card reader)

---

## 1. Agent Overview

### 1.1 Architecture

```
+----------------------------------------+
|            Store PC (Windows)           |
|                                        |
|  +----------------------------------+  |
|  |      TMS Agent (Python)          |  |
|  |                                  |  |
|  |  +-------------+ +-------------+ |  |
|  |  |  Main Loop  | |  API Client | |  |
|  |  +------+------+ +-------+-----+ |  |
|  |         |                |       |  |
|  |  +------+------+ +-------+------+|  |
|  |  | USB Monitor | | Heartbeat    ||  |
|  |  +------+------+ +-------+------+|  |
|  |         |                |       |  |
|  |  +------+----------------+------+|  |
|  |  |   TC-200 Controller (DLL)    ||  |
|  |  +---------------+--------------+|  |
|  +------------------+---------------+  |
|                     |                  |
|          +----------+----------+       |
|          |  TC-200.dll         |       |
|          +----------+----------+       |
|                     |                  |
|          +----------+----------+       |
|          |  TC-200 Terminal    |       |
|          |  (USB Connection)   |       |
|          +---------------------+       |
+----------------------------------------+
```

### 1.2 Main Features

| Feature | Description | Execution Frequency |
|---------|-------------|---------------------|
| Heartbeat transmission | Survival notification to server | Every 5 minutes |
| Terminal status monitoring | USB connection status check | Every 30 seconds |
| Metrics collection | CPU/memory usage | Every 5 minutes |
| Firmware update | Remote update execution | On demand |
| Log transmission | Error log upload | On occurrence |
| Auto recovery | Reconnection on connection error | On error detection |

---

## 2. Directory Structure

```
agent/
├── main.py                 # Main entry point
├── config.py               # Configuration management
├── terminal_controller.py  # TC-200 control
├── api_client.py           # API communication
├── monitoring.py           # System monitoring
├── updater.py              # Auto update feature
├── logger.py               # Log management
├── utils.py                # Utilities
├── requirements.txt        # Dependencies
├── config.ini              # Configuration file
├── install.py              # Installer
├── service.py              # Windows service
└── dll/
    └── TC-200.dll          # Terminal control DLL
```

---

## 3. Detailed Implementation

### 3.1 Main Program (main.py)

```python
# agent/main.py

import sys
import time
import signal
import logging
import threading
from datetime import datetime
from config import Config
from terminal_controller import TerminalController
from api_client import APIClient
from monitoring import SystemMonitor
from updater import AutoUpdater

class TMSAgent:
    """TMS Agent main class"""

    def __init__(self):
        """Initialization"""
        # Load configuration
        self.config = Config('config.ini')

        # Initialize logger
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.terminal = TerminalController(self.config.dll_path)
        self.api = APIClient(
            self.config.server_url,
            self.config.api_key
        )
        self.monitor = SystemMonitor()
        self.updater = AutoUpdater(self.config)

        # Execution flags
        self.running = False
        self.threads = []

        # Signal handler setup
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def setup_logging(self):
        """Log configuration"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_file = f'logs/agent_{datetime.now():%Y%m%d}.log'

        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def start(self):
        """Start agent"""
        self.logger.info("Starting TMS Agent")
        self.running = True

        # Check terminal connection
        if not self.check_terminal_connection():
            self.logger.error("TC-200 terminal not detected")
            return False

        # Initial registration
        if not self.register_agent():
            self.logger.error("Server registration failed")
            return False

        # Start monitoring threads
        self.start_monitoring_threads()

        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self.shutdown()
        return True

    def check_terminal_connection(self):
        """Check terminal connection"""
        try:
            # USB connection check
            if not self.terminal.is_connected():
                self.logger.warning("Terminal is not connected")

                # Auto-detection attempt
                self.logger.info("Searching for terminal...")
                devices = self.terminal.scan_devices()

                if devices:
                    # Connect to first device
                    if self.terminal.connect(devices[0]):
                        self.logger.info(f"Connected to terminal: {devices[0]}")
                        return True

                return False

            # Get terminal information
            info = self.terminal.get_device_info()
            self.logger.info(f"Terminal detected: {info['serial_number']}")

            return True

        except Exception as e:
            self.logger.error(f"Terminal connection error: {e}")
            return False

    def register_agent(self):
        """Server registration"""
        try:
            # Collect terminal information
            terminal_info = self.terminal.get_device_info()
            system_info = self.monitor.get_system_info()

            # Create registration data
            registration_data = {
                "serial_number": terminal_info['serial_number'],
                "firmware_version": terminal_info['firmware_version'],
                "agent_version": self.config.agent_version,
                "hostname": system_info['hostname'],
                "os_version": system_info['os_version'],
                "ip_address": system_info['ip_address']
            }

            # Server registration
            response = self.api.register(registration_data)

            if response['status'] == 'success':
                self.logger.info("Server registration complete")
                # Save token
                self.config.save_token(response['token'])
                return True

            return False

        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False

    def start_monitoring_threads(self):
        """Start monitoring threads"""
        # Heartbeat thread
        heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop,
            daemon=True
        )
        heartbeat_thread.start()
        self.threads.append(heartbeat_thread)

        # Terminal monitoring thread
        terminal_thread = threading.Thread(
            target=self.terminal_monitor_loop,
            daemon=True
        )
        terminal_thread.start()
        self.threads.append(terminal_thread)

        # Update check thread
        update_thread = threading.Thread(
            target=self.update_check_loop,
            daemon=True
        )
        update_thread.start()
        self.threads.append(update_thread)

        self.logger.info("Monitoring threads started")

    def heartbeat_loop(self):
        """Heartbeat transmission loop"""
        while self.running:
            try:
                # Collect metrics
                metrics = self.monitor.get_metrics()
                terminal_status = self.terminal.get_status()

                # Heartbeat data
                heartbeat_data = {
                    "serial_number": self.terminal.serial_number,
                    "status": "online" if terminal_status['connected'] else "offline",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "cpu_usage": metrics['cpu_usage'],
                        "memory_usage": metrics['memory_usage'],
                        "disk_usage": metrics['disk_usage'],
                        "uptime": metrics['uptime']
                    },
                    "terminal": {
                        "firmware_version": terminal_status['firmware_version'],
                        "transaction_count": terminal_status['transaction_count'],
                        "last_transaction": terminal_status['last_transaction']
                    }
                }

                # Send to server
                response = self.api.send_heartbeat(heartbeat_data)

                # Process commands
                if 'commands' in response:
                    self.process_commands(response['commands'])

                self.logger.debug("Heartbeat transmission complete")

            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")

            # Wait 5 minutes
            time.sleep(300)

    def terminal_monitor_loop(self):
        """Terminal monitoring loop"""
        error_count = 0
        max_errors = 5

        while self.running:
            try:
                # Check USB connection status
                if not self.terminal.is_connected():
                    self.logger.warning("Connection to terminal lost")

                    # Reconnection attempt
                    if self.terminal.reconnect():
                        self.logger.info("Reconnected to terminal")
                        error_count = 0

                        # Disconnection event notification
                        self.api.send_event({
                            "type": "reconnected",
                            "serial_number": self.terminal.serial_number,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        error_count += 1

                        if error_count >= max_errors:
                            # Send error alert
                            self.api.send_alert({
                                "type": "connection_lost",
                                "serial_number": self.terminal.serial_number,
                                "message": "Connection to terminal cannot be recovered",
                                "timestamp": datetime.now().isoformat()
                            })

                            # Reset error count (for next retry)
                            error_count = 0
                else:
                    # Check terminal status
                    status = self.terminal.get_detailed_status()

                    # Error detection
                    if status['has_error']:
                        self.logger.error(f"Terminal error: {status['error_code']}")

                        # Error notification
                        self.api.send_alert({
                            "type": "terminal_error",
                            "serial_number": self.terminal.serial_number,
                            "error_code": status['error_code'],
                            "error_message": status['error_message'],
                            "timestamp": datetime.now().isoformat()
                        })

            except Exception as e:
                self.logger.error(f"Terminal monitoring error: {e}")

            # Wait 30 seconds
            time.sleep(30)

    def update_check_loop(self):
        """Update check loop"""
        while self.running:
            try:
                # Check for agent update
                if self.updater.check_agent_update():
                    self.logger.info("Agent update available")

                    # Execute auto update
                    if self.config.auto_update_enabled:
                        self.perform_agent_update()

                # Check for firmware update
                firmware_update = self.api.check_firmware_update(
                    self.terminal.serial_number
                )

                if firmware_update:
                    self.logger.info(f"Firmware update: {firmware_update['version']}")
                    self.perform_firmware_update(firmware_update)

            except Exception as e:
                self.logger.error(f"Update check error: {e}")

            # Wait 1 hour
            time.sleep(3600)

    def process_commands(self, commands):
        """Process remote commands"""
        for command in commands:
            try:
                self.logger.info(f"Executing command: {command['type']}")

                if command['type'] == 'restart':
                    self.restart_terminal()

                elif command['type'] == 'update_firmware':
                    self.perform_firmware_update(command['params'])

                elif command['type'] == 'collect_logs':
                    self.send_logs()

                elif command['type'] == 'run_diagnostic':
                    self.run_diagnostics()

                elif command['type'] == 'update_config':
                    self.update_configuration(command['params'])

                else:
                    self.logger.warning(f"Unknown command: {command['type']}")

                # Command completion notification
                self.api.send_command_result({
                    "command_id": command['id'],
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                self.logger.error(f"Command execution error: {e}")

                # Error notification
                self.api.send_command_result({
                    "command_id": command['id'],
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

    def restart_terminal(self):
        """Restart terminal"""
        self.logger.info("Restarting terminal")

        # Reset terminal
        self.terminal.reset()
        time.sleep(5)

        # Reconnect
        self.terminal.reconnect()

    def perform_firmware_update(self, update_info):
        """Execute firmware update"""
        try:
            self.logger.info(f"Starting firmware update: {update_info['version']}")

            # Download firmware
            firmware_file = self.api.download_firmware(
                update_info['download_url']
            )

            # Execute update
            result = self.terminal.update_firmware(firmware_file)

            if result['success']:
                self.logger.info("Firmware update complete")

                # Success notification
                self.api.send_update_result({
                    "serial_number": self.terminal.serial_number,
                    "version": update_info['version'],
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                raise Exception(result['error'])

        except Exception as e:
            self.logger.error(f"Firmware update failed: {e}")

            # Failure notification
            self.api.send_update_result({
                "serial_number": self.terminal.serial_number,
                "version": update_info['version'],
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def perform_agent_update(self):
        """Agent self-update"""
        try:
            self.logger.info("Starting agent update")

            # Execute update
            if self.updater.update():
                self.logger.info("Agent update complete, restarting")

                # Restart
                self.restart_agent()

        except Exception as e:
            self.logger.error(f"Agent update failed: {e}")

    def send_logs(self):
        """Send logs"""
        try:
            # Collect log files
            log_files = self.collect_log_files()

            # Compress
            archive = self.compress_logs(log_files)

            # Upload
            self.api.upload_logs(archive)

            self.logger.info("Log transmission complete")

        except Exception as e:
            self.logger.error(f"Log transmission error: {e}")

    def run_diagnostics(self):
        """Execute diagnostics"""
        try:
            self.logger.info("Starting diagnostics")

            # Execute diagnostic items
            diagnostics = {
                "terminal_test": self.terminal.run_self_test(),
                "network_test": self.test_network_connectivity(),
                "system_check": self.monitor.run_system_check(),
                "timestamp": datetime.now().isoformat()
            }

            # Send results
            self.api.send_diagnostics(diagnostics)

            self.logger.info("Diagnostics complete")

        except Exception as e:
            self.logger.error(f"Diagnostics error: {e}")

    def shutdown(self, signum=None, frame=None):
        """Shutdown processing"""
        self.logger.info("Stopping agent")
        self.running = False

        # Wait for threads to stop
        for thread in self.threads:
            thread.join(timeout=5)

        # Disconnection notification
        try:
            self.api.send_event({
                "type": "agent_shutdown",
                "serial_number": self.terminal.serial_number,
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass

        # Resource cleanup
        self.terminal.disconnect()

        self.logger.info("Agent stopped")
        sys.exit(0)

    def restart_agent(self):
        """Restart agent"""
        import os
        import subprocess

        self.logger.info("Restarting agent")

        # Start new process
        subprocess.Popen([sys.executable] + sys.argv)

        # Exit current process
        self.shutdown()


def main():
    """Main entry point"""
    agent = TMSAgent()
    agent.start()


if __name__ == "__main__":
    main()
```

### 3.2 Terminal Controller (terminal_controller.py)

```python
# agent/terminal_controller.py

import ctypes
import time
import logging
from typing import Dict, List, Optional, Any

class TerminalController:
    """TC-200 terminal control class"""

    def __init__(self, dll_path: str = "dll/TC-200.dll"):
        """
        Initialization

        Args:
            dll_path: Path to TC-200.dll
        """
        self.logger = logging.getLogger(__name__)
        self.dll_path = dll_path
        self.dll = None
        self.serial_number = None
        self.connected = False

        # Load DLL
        self.load_dll()

    def load_dll(self):
        """Load DLL"""
        try:
            self.dll = ctypes.CDLL(self.dll_path)

            # Function definitions
            self.setup_dll_functions()

            self.logger.info(f"DLL loaded: {self.dll_path}")

        except Exception as e:
            self.logger.error(f"DLL load error: {e}")
            raise

    def setup_dll_functions(self):
        """DLL function definitions"""
        # Initialize
        self.dll.Initialize.argtypes = []
        self.dll.Initialize.restype = ctypes.c_int

        # Device scan
        self.dll.ScanDevices.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int
        ]
        self.dll.ScanDevices.restype = ctypes.c_int

        # Connect
        self.dll.Connect.argtypes = [ctypes.c_char_p]
        self.dll.Connect.restype = ctypes.c_int

        # Disconnect
        self.dll.Disconnect.argtypes = []
        self.dll.Disconnect.restype = ctypes.c_int

        # Get status
        self.dll.GetStatus.argtypes = [ctypes.POINTER(StatusInfo)]
        self.dll.GetStatus.restype = ctypes.c_int

        # Get device info
        self.dll.GetDeviceInfo.argtypes = [ctypes.POINTER(DeviceInfo)]
        self.dll.GetDeviceInfo.restype = ctypes.c_int

        # Firmware update
        self.dll.UpdateFirmware.argtypes = [ctypes.c_char_p]
        self.dll.UpdateFirmware.restype = ctypes.c_int

        # Self test
        self.dll.RunSelfTest.argtypes = []
        self.dll.RunSelfTest.restype = ctypes.c_int

        # Reset
        self.dll.Reset.argtypes = []
        self.dll.Reset.restype = ctypes.c_int

    def scan_devices(self) -> List[str]:
        """
        Scan for USB-connected TC-200 devices

        Returns:
            List of detected device serial numbers
        """
        try:
            # Prepare buffer
            max_devices = 10
            device_array = (ctypes.c_char_p * max_devices)()

            # Execute scan
            count = self.dll.ScanDevices(device_array, max_devices)

            # Get results
            devices = []
            for i in range(count):
                if device_array[i]:
                    devices.append(device_array[i].decode('utf-8'))

            self.logger.info(f"{count} devices detected")
            return devices

        except Exception as e:
            self.logger.error(f"Device scan error: {e}")
            return []

    def connect(self, serial_number: str = None) -> bool:
        """
        Connect to terminal

        Args:
            serial_number: Serial number of device to connect

        Returns:
            True if connection successful
        """
        try:
            # Disconnect if already connected
            if self.connected:
                self.disconnect()

            # Connect to first device if serial number not specified
            if not serial_number:
                devices = self.scan_devices()
                if not devices:
                    self.logger.error("No available devices found")
                    return False
                serial_number = devices[0]

            # Execute connection
            result = self.dll.Connect(serial_number.encode('utf-8'))

            if result == 0:
                self.serial_number = serial_number
                self.connected = True
                self.logger.info(f"Connected to terminal: {serial_number}")
                return True
            else:
                self.logger.error(f"Connection failed: error code {result}")
                return False

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from terminal"""
        try:
            if self.connected:
                self.dll.Disconnect()
                self.connected = False
                self.logger.info("Disconnected from terminal")

        except Exception as e:
            self.logger.error(f"Disconnection error: {e}")

    def is_connected(self) -> bool:
        """
        Check connection status

        Returns:
            True if connected
        """
        try:
            if not self.connected:
                return False

            # Check actual connection status
            status = StatusInfo()
            result = self.dll.GetStatus(ctypes.byref(status))

            if result != 0:
                self.connected = False
                return False

            return True

        except:
            self.connected = False
            return False

    def reconnect(self) -> bool:
        """
        Reconnect

        Returns:
            True if reconnection successful
        """
        self.logger.info("Attempting reconnection")

        # Disconnect first
        self.disconnect()
        time.sleep(2)

        # Reconnect
        return self.connect(self.serial_number)

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information

        Returns:
            Dictionary of device information
        """
        try:
            info = DeviceInfo()
            result = self.dll.GetDeviceInfo(ctypes.byref(info))

            if result == 0:
                return {
                    "serial_number": info.serial_number.decode('utf-8'),
                    "firmware_version": info.firmware_version.decode('utf-8'),
                    "model": info.model.decode('utf-8'),
                    "manufacturer": "TechCore Solutions"
                }
            else:
                raise Exception(f"Failed to get info: error code {result}")

        except Exception as e:
            self.logger.error(f"Device info retrieval error: {e}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """
        Get terminal status

        Returns:
            Dictionary of status information
        """
        try:
            status = StatusInfo()
            result = self.dll.GetStatus(ctypes.byref(status))

            if result == 0:
                return {
                    "connected": True,
                    "firmware_version": status.firmware_version.decode('utf-8'),
                    "transaction_count": status.transaction_count,
                    "last_transaction": status.last_transaction,
                    "error_code": status.error_code
                }
            else:
                return {
                    "connected": False,
                    "error": f"Failed to get status: {result}"
                }

        except Exception as e:
            self.logger.error(f"Status retrieval error: {e}")
            return {"connected": False, "error": str(e)}

    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed status

        Returns:
            Detailed status information
        """
        basic_status = self.get_status()

        # Error determination
        has_error = basic_status.get('error_code', 0) != 0

        # Get error message
        error_message = ""
        if has_error:
            error_message = self.get_error_message(basic_status['error_code'])

        return {
            **basic_status,
            "has_error": has_error,
            "error_message": error_message
        }

    def get_error_message(self, error_code: int) -> str:
        """
        Get message from error code

        Args:
            error_code: Error code

        Returns:
            Error message
        """
        error_messages = {
            1: "Communication error",
            2: "Hardware error",
            3: "Firmware error",
            4: "Memory error",
            5: "Configuration error",
            10: "Card reader error",
            11: "Printer error",
            20: "Temperature abnormality",
            21: "Voltage abnormality"
        }

        return error_messages.get(error_code, f"Unknown error ({error_code})")

    def update_firmware(self, firmware_file: str) -> Dict[str, Any]:
        """
        Firmware update

        Args:
            firmware_file: Firmware file path

        Returns:
            Update result
        """
        try:
            self.logger.info(f"Starting firmware update: {firmware_file}")

            # Execute update
            result = self.dll.UpdateFirmware(firmware_file.encode('utf-8'))

            if result == 0:
                self.logger.info("Firmware update successful")

                # Wait for reboot
                time.sleep(10)

                # Reconnect
                self.reconnect()

                return {"success": True}
            else:
                error_msg = f"Firmware update failed: error code {result}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Firmware update error: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def run_self_test(self) -> Dict[str, Any]:
        """
        Execute self-test

        Returns:
            Test results
        """
        try:
            self.logger.info("Starting self-test")

            result = self.dll.RunSelfTest()

            test_results = {
                "success": result == 0,
                "tests": {
                    "memory": (result & 0x01) == 0,
                    "communication": (result & 0x02) == 0,
                    "card_reader": (result & 0x04) == 0,
                    "printer": (result & 0x08) == 0,
                    "display": (result & 0x10) == 0,
                    "keypad": (result & 0x20) == 0
                }
            }

            self.logger.info(f"Self-test complete: {test_results}")
            return test_results

        except Exception as e:
            self.logger.error(f"Self-test error: {e}")
            return {"success": False, "error": str(e)}

    def reset(self):
        """Reset terminal"""
        try:
            self.logger.info("Resetting terminal")
            self.dll.Reset()

        except Exception as e:
            self.logger.error(f"Reset error: {e}")


# C structure definitions
class StatusInfo(ctypes.Structure):
    """Status information structure"""
    _fields_ = [
        ("firmware_version", ctypes.c_char * 20),
        ("transaction_count", ctypes.c_int),
        ("last_transaction", ctypes.c_int),
        ("error_code", ctypes.c_int)
    ]


class DeviceInfo(ctypes.Structure):
    """Device information structure"""
    _fields_ = [
        ("serial_number", ctypes.c_char * 50),
        ("firmware_version", ctypes.c_char * 20),
        ("model", ctypes.c_char * 30)
    ]
```

### 3.3 API Client (api_client.py)

```python
# agent/api_client.py

import json
import requests
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

class APIClient:
    """TMS server API client"""

    def __init__(self, server_url: str, api_key: str = None):
        """
        Initialization

        Args:
            server_url: TMS server URL
            api_key: API key
        """
        self.logger = logging.getLogger(__name__)
        self.server_url = server_url
        self.api_key = api_key
        self.token = None
        self.session = requests.Session()

        # Default header settings
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TMS-Agent/1.0'
        })

        if api_key:
            self.session.headers['X-API-Key'] = api_key

    def register(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent registration

        Args:
            registration_data: Registration data

        Returns:
            Response data
        """
        url = urljoin(self.server_url, '/api/agent/register')

        try:
            response = self.session.post(url, json=registration_data)
            response.raise_for_status()

            data = response.json()

            # Save token
            if 'token' in data:
                self.token = data['token']
                self.session.headers['Authorization'] = f"Bearer {self.token}"

            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Registration error: {e}")
            return {"status": "error", "message": str(e)}

    def send_heartbeat(self, heartbeat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send heartbeat

        Args:
            heartbeat_data: Heartbeat data

        Returns:
            Response data (including commands)
        """
        url = urljoin(self.server_url, '/api/heartbeat')

        try:
            response = self.session.post(url, json=heartbeat_data, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            self.logger.warning("Heartbeat timeout")
            return {}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Heartbeat error: {e}")
            return {}

    def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert

        Args:
            alert_data: Alert data

        Returns:
            True if transmission successful
        """
        url = urljoin(self.server_url, '/api/alerts')

        try:
            response = self.session.post(url, json=alert_data)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Alert transmission error: {e}")
            return False

    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Send event

        Args:
            event_data: Event data

        Returns:
            True if transmission successful
        """
        url = urljoin(self.server_url, '/api/events')

        try:
            response = self.session.post(url, json=event_data)
            response.raise_for_status()
            return True

        except:
            return False

    def check_firmware_update(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """
        Check for firmware update

        Args:
            serial_number: Serial number

        Returns:
            Update information (if available)
        """
        url = urljoin(self.server_url, f'/api/firmware/check/{serial_number}')

        try:
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get('update_available'):
                return data['update_info']

            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Update check error: {e}")
            return None

    def download_firmware(self, download_url: str) -> str:
        """
        Download firmware

        Args:
            download_url: Download URL

        Returns:
            Saved file path
        """
        import os
        import tempfile

        try:
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()

            # Save to temporary file
            fd, filepath = tempfile.mkstemp(suffix='.bin')

            with os.fdopen(fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"Firmware download complete: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            raise

    def send_command_result(self, result_data: Dict[str, Any]) -> bool:
        """
        Send command execution result

        Args:
            result_data: Execution result data

        Returns:
            True if transmission successful
        """
        url = urljoin(self.server_url, '/api/commands/result')

        try:
            response = self.session.post(url, json=result_data)
            response.raise_for_status()
            return True

        except:
            return False

    def send_update_result(self, result_data: Dict[str, Any]) -> bool:
        """
        Send update result

        Args:
            result_data: Update result data

        Returns:
            True if transmission successful
        """
        url = urljoin(self.server_url, '/api/firmware/result')

        try:
            response = self.session.post(url, json=result_data)
            response.raise_for_status()
            return True

        except:
            return False

    def upload_logs(self, log_archive: str) -> bool:
        """
        Upload logs

        Args:
            log_archive: Log archive file path

        Returns:
            True if upload successful
        """
        url = urljoin(self.server_url, '/api/logs/upload')

        try:
            with open(log_archive, 'rb') as f:
                files = {'logs': f}
                response = self.session.post(url, files=files)
                response.raise_for_status()

            return True

        except Exception as e:
            self.logger.error(f"Log upload error: {e}")
            return False

    def send_diagnostics(self, diagnostics_data: Dict[str, Any]) -> bool:
        """
        Send diagnostics results

        Args:
            diagnostics_data: Diagnostics result data

        Returns:
            True if transmission successful
        """
        url = urljoin(self.server_url, '/api/diagnostics')

        try:
            response = self.session.post(url, json=diagnostics_data)
            response.raise_for_status()
            return True

        except:
            return False
```

---

## 4. Configuration File

### 4.1 Configuration File (config.ini)

```ini
# agent/config.ini

[server]
# TMS server URL
url = https://tms.techcore-solutions.jp

# API key (obtained at initial registration)
api_key =

# Authentication token (automatically set)
token =

[agent]
# Agent version
version = 1.0.0

# Enable auto update
auto_update = true

# Log level (DEBUG, INFO, WARNING, ERROR)
log_level = INFO

# Log retention days
log_retention_days = 30

[terminal]
# DLL path
dll_path = dll/TC-200.dll

# Reconnection attempts
reconnect_attempts = 5

# Reconnection delay (seconds)
reconnect_delay = 10

[monitoring]
# Heartbeat interval (seconds)
heartbeat_interval = 300

# Terminal check interval (seconds)
terminal_check_interval = 30

# Update check interval (seconds)
update_check_interval = 3600

[network]
# Proxy settings
use_proxy = false
proxy_url =

# Timeout (seconds)
timeout = 30

# Retry count
max_retries = 3
```

---

## 5. Installer

### 5.1 Installation Script (install.py)

```python
# agent/install.py

import os
import sys
import shutil
import winreg
import logging
from pathlib import Path

class AgentInstaller:
    """TMS Agent installer"""

    def __init__(self):
        self.install_dir = Path(r"C:\Program Files\TechCore\TMS Agent")
        self.service_name = "TechCoreTMSAgent"
        self.logger = self.setup_logging()

    def setup_logging(self):
        """Log configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def install(self):
        """Execute installation"""
        try:
            self.logger.info("Starting TMS Agent installation")

            # Check administrator privileges
            if not self.is_admin():
                self.logger.error("Please run as administrator")
                return False

            # Create directories
            self.create_directories()

            # Copy files
            self.copy_files()

            # Install dependencies
            self.install_dependencies()

            # Register Windows service
            self.register_service()

            # Registry settings
            self.setup_registry()

            # Add firewall exception
            self.setup_firewall()

            self.logger.info("Installation complete")
            return True

        except Exception as e:
            self.logger.error(f"Installation error: {e}")
            return False

    def is_admin(self):
        """Check administrator privileges"""
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()

    def create_directories(self):
        """Create directories"""
        dirs = [
            self.install_dir,
            self.install_dir / "logs",
            self.install_dir / "dll",
            self.install_dir / "temp"
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Directory created: {dir_path}")

    def copy_files(self):
        """Copy files"""
        files = [
            "main.py",
            "config.py",
            "terminal_controller.py",
            "api_client.py",
            "monitoring.py",
            "updater.py",
            "logger.py",
            "utils.py",
            "config.ini",
            "requirements.txt",
            "service.py"
        ]

        for file in files:
            src = Path(file)
            dst = self.install_dir / file

            if src.exists():
                shutil.copy2(src, dst)
                self.logger.info(f"File copied: {file}")

        # Copy DLL
        dll_src = Path("dll/TC-200.dll")
        if dll_src.exists():
            shutil.copy2(dll_src, self.install_dir / "dll" / "TC-200.dll")

    def install_dependencies(self):
        """Install dependencies"""
        import subprocess

        self.logger.info("Installing dependencies...")

        subprocess.check_call([
            sys.executable,
            "-m", "pip", "install",
            "-r", str(self.install_dir / "requirements.txt")
        ])

    def register_service(self):
        """Register Windows service"""
        import subprocess

        service_path = self.install_dir / "service.py"

        # Using nssm (requires separate installation)
        nssm_path = "nssm.exe"

        commands = [
            [nssm_path, "install", self.service_name, sys.executable, str(service_path)],
            [nssm_path, "set", self.service_name, "AppDirectory", str(self.install_dir)],
            [nssm_path, "set", self.service_name, "Description", "TechCore TMS Agent Service"],
            [nssm_path, "set", self.service_name, "Start", "SERVICE_AUTO_START"]
        ]

        for cmd in commands:
            subprocess.check_call(cmd)

        self.logger.info(f"Service registered: {self.service_name}")

    def setup_registry(self):
        """Registry settings"""
        try:
            # Add uninstall information
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TechCoreTMSAgent"

            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "TechCore TMS Agent")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "TechCore Solutions")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.install_dir))
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                                str(self.install_dir / "uninstall.exe"))

            self.logger.info("Registry settings complete")

        except Exception as e:
            self.logger.warning(f"Registry settings error: {e}")

    def setup_firewall(self):
        """Firewall settings"""
        import subprocess

        try:
            # Allow outbound communication
            subprocess.check_call([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=TechCore TMS Agent",
                "dir=out",
                "action=allow",
                f"program={self.install_dir / 'main.py'}"
            ])

            self.logger.info("Firewall settings complete")

        except Exception as e:
            self.logger.warning(f"Firewall settings error: {e}")

    def start_service(self):
        """Start service"""
        import subprocess

        try:
            subprocess.check_call(["net", "start", self.service_name])
            self.logger.info("Service started")
        except:
            self.logger.warning("Failed to start service")


def main():
    """Main process"""
    installer = AgentInstaller()

    if installer.install():
        print("\n=== Installation Complete ===")
        print(f"Installation directory: {installer.install_dir}")
        print(f"Service name: {installer.service_name}")
        print("\nStart service? (y/n): ", end="")

        if input().lower() == 'y':
            installer.start_service()
    else:
        print("\nInstallation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Summary

With this agent implementation specification:

1. **Agent program that operates autonomously** on store PCs
2. **Controls USB-connected TC-200 terminals**
3. **Sends heartbeat every 5 minutes**
4. **Automatic alerts on anomaly detection**
5. **Remote firmware update support**
6. **Runs as a Windows service**

Devin can fully implement based on this specification.
