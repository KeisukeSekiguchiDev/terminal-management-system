import sys
import time
import signal
import logging
import threading
from datetime import datetime
from pathlib import Path

from config import Config
from terminal_controller import TerminalController
from api_client import APIClient
from monitoring import SystemMonitor


class TMSAgent:
    """TMS Agent main class"""
    
    def __init__(self):
        """Initialize agent"""
        self.config = Config('config.ini')
        
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        self.terminal = TerminalController(self.config.dll_path)
        self.api = APIClient(self.config.server_url, self.config.api_key)
        self.monitor = SystemMonitor()
        
        self.running = False
        self.threads = []
        
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def setup_logging(self):
        """Configure logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_file = Path(self.config.log_dir) / f'agent_{datetime.now():%Y%m%d}.log'
        
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
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
        
        if not self.check_terminal_connection():
            self.logger.error("TC-200 terminal not detected")
            return False
        
        if not self.register_agent():
            self.logger.error("Server registration failed")
            return False
        
        self.start_monitoring_threads()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        self.shutdown()
        return True
    
    def check_terminal_connection(self) -> bool:
        """Check terminal connection"""
        try:
            if not self.terminal.is_connected():
                self.logger.warning("Terminal is not connected")
                
                self.logger.info("Searching for terminal...")
                devices = self.terminal.scan_devices()
                
                if devices:
                    if self.terminal.connect(devices[0]):
                        self.logger.info(f"Connected to terminal: {devices[0]}")
                        return True
                
                return False
            
            info = self.terminal.get_device_info()
            self.logger.info(f"Terminal detected: {info.get('serial_number')}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Terminal connection error: {e}")
            return False
    
    def register_agent(self) -> bool:
        """Register with server"""
        try:
            terminal_info = self.terminal.get_device_info()
            system_info = self.monitor.get_system_info()
            
            registration_data = {
                "serial_number": terminal_info.get('serial_number'),
                "firmware_version": terminal_info.get('firmware_version'),
                "agent_version": self.config.agent_version,
                "hostname": system_info.get('hostname'),
                "os_version": system_info.get('os_version'),
                "ip_address": system_info.get('ip_address')
            }
            
            response = self.api.register(registration_data)
            
            if response.get('status') == 'success':
                self.logger.info("Server registration complete")
                if response.get('token'):
                    self.config.save_token(response['token'])
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
    
    def start_monitoring_threads(self):
        """Start monitoring threads"""
        heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop,
            daemon=True
        )
        heartbeat_thread.start()
        self.threads.append(heartbeat_thread)
        
        terminal_thread = threading.Thread(
            target=self.terminal_monitor_loop,
            daemon=True
        )
        terminal_thread.start()
        self.threads.append(terminal_thread)
        
        self.logger.info("Monitoring threads started")
    
    def heartbeat_loop(self):
        """Heartbeat transmission loop"""
        while self.running:
            try:
                metrics = self.monitor.get_metrics()
                terminal_status = self.terminal.get_status()
                terminal_info = self.terminal.get_device_info()
                
                heartbeat_data = {
                    "serial_number": terminal_info.get('serial_number'),
                    "status": terminal_status.get('status', 'offline'),
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "cpu_usage": metrics.get('cpu_usage', 0),
                        "memory_usage": metrics.get('memory_usage', 0),
                        "disk_usage": metrics.get('disk_usage', 0),
                        "temperature": 45
                    },
                    "firmware_version": terminal_info.get('firmware_version'),
                    "agent_version": self.config.agent_version,
                    "ip_address": self.monitor.get_ip_address()
                }
                
                response = self.api.send_heartbeat(heartbeat_data)
                
                if 'commands' in response:
                    self.process_commands(response['commands'])
                
                self.logger.debug("Heartbeat transmission complete")
            
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
            
            time.sleep(self.config.heartbeat_interval)
    
    def terminal_monitor_loop(self):
        """Terminal monitoring loop"""
        error_count = 0
        max_errors = 5
        
        while self.running:
            try:
                if not self.terminal.is_connected():
                    self.logger.warning("Connection to terminal lost")
                    
                    if self.terminal.reconnect():
                        self.logger.info("Reconnected to terminal")
                        error_count = 0
                        
                        self.api.send_event({
                            "type": "reconnected",
                            "serial_number": self.terminal.serial_number,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        error_count += 1
                        
                        if error_count >= max_errors:
                            self.api.send_alert({
                                "type": "connection_lost",
                                "serial_number": self.terminal.serial_number,
                                "message": "Connection to terminal cannot be recovered",
                                "timestamp": datetime.now().isoformat()
                            })
                            error_count = 0
                else:
                    status = self.terminal.get_detailed_status()
                    
                    if status.get('has_error'):
                        self.logger.error(f"Terminal error: {status.get('error_code')}")
                        
                        self.api.send_alert({
                            "type": "terminal_error",
                            "serial_number": self.terminal.serial_number,
                            "error_code": status.get('error_code'),
                            "error_message": status.get('error_message'),
                            "timestamp": datetime.now().isoformat()
                        })
            
            except Exception as e:
                self.logger.error(f"Terminal monitoring error: {e}")
            
            time.sleep(30)
    
    def process_commands(self, commands):
        """Process remote commands"""
        for command in commands:
            try:
                self.logger.info(f"Executing command: {command.get('type')}")
                
                command_type = command.get('type')
                
                if command_type == 'reboot':
                    self.restart_terminal()
                elif command_type == 'firmware':
                    self.perform_firmware_update(command.get('parameters', {}))
                elif command_type == 'config':
                    self.update_configuration(command.get('parameters', {}))
                else:
                    self.logger.warning(f"Unknown command: {command_type}")
                
                self.api.send_command_result({
                    "command_id": command.get('id'),
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
            
            except Exception as e:
                self.logger.error(f"Command execution error: {e}")
                
                self.api.send_command_result({
                    "command_id": command.get('id'),
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
    
    def restart_terminal(self):
        """Restart terminal"""
        self.logger.info("Restarting terminal")
        self.terminal.reset()
        time.sleep(5)
        self.terminal.reconnect()
    
    def perform_firmware_update(self, update_info):
        """Execute firmware update"""
        try:
            self.logger.info(f"Starting firmware update: {update_info.get('version')}")
            
            firmware_file = Path(self.config.temp_dir) / 'firmware.bin'
            
            if update_info.get('url'):
                self.api.download_firmware(update_info['url'], str(firmware_file))
            
            result = self.terminal.update_firmware(str(firmware_file))
            
            if result.get('success'):
                self.logger.info("Firmware update complete")
                
                self.api.send_update_result({
                    "serial_number": self.terminal.serial_number,
                    "version": update_info.get('version'),
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                raise Exception(result.get('error'))
        
        except Exception as e:
            self.logger.error(f"Firmware update failed: {e}")
            
            self.api.send_update_result({
                "serial_number": self.terminal.serial_number,
                "version": update_info.get('version'),
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    def update_configuration(self, config_params):
        """Update configuration"""
        try:
            self.logger.info("Updating configuration")
            
            for key, value in config_params.items():
                section, param = key.split('.', 1)
                self.config.set(section, param, value)
            
            self.logger.info("Configuration updated")
        
        except Exception as e:
            self.logger.error(f"Configuration update error: {e}")
    
    def shutdown(self, signum=None, frame=None):
        """Shutdown processing"""
        self.logger.info("Stopping agent")
        self.running = False
        
        for thread in self.threads:
            thread.join(timeout=5)
        
        try:
            self.api.send_event({
                "type": "agent_shutdown",
                "serial_number": self.terminal.serial_number,
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
        
        self.terminal.disconnect()
        
        self.logger.info("Agent stopped")
        sys.exit(0)


def main():
    """Main entry point"""
    agent = TMSAgent()
    agent.start()


if __name__ == "__main__":
    main()
