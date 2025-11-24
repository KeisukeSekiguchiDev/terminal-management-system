import os
import configparser
import json
from pathlib import Path


class Config:
    """Configuration management for TMS Agent"""
    
    def __init__(self, config_file='config.ini'):
        """
        Initialize configuration
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        if os.path.exists(config_file):
            self.config.read(config_file)
        else:
            self._create_default_config()
        
        self._load_config()
    
    def _create_default_config(self):
        """Create default configuration file"""
        self.config['Server'] = {
            'url': 'https://tms-api.techcore.com/api/v1',
            'timeout': '30'
        }
        
        self.config['Agent'] = {
            'version': '1.0.0',
            'heartbeat_interval': '300',
            'auto_update_enabled': 'true',
            'log_level': 'INFO'
        }
        
        self.config['Terminal'] = {
            'dll_path': 'dll/TC-200.dll',
            'connection_timeout': '10',
            'retry_attempts': '3'
        }
        
        self.config['Paths'] = {
            'log_dir': 'logs',
            'data_dir': 'data',
            'temp_dir': 'temp'
        }
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def _load_config(self):
        """Load configuration values"""
        self.server_url = self.config.get('Server', 'url')
        self.server_timeout = self.config.getint('Server', 'timeout')
        
        self.agent_version = self.config.get('Agent', 'version')
        self.heartbeat_interval = self.config.getint('Agent', 'heartbeat_interval')
        self.auto_update_enabled = self.config.getboolean('Agent', 'auto_update_enabled')
        self.log_level = self.config.get('Agent', 'log_level')
        
        self.dll_path = self.config.get('Terminal', 'dll_path')
        self.connection_timeout = self.config.getint('Terminal', 'connection_timeout')
        self.retry_attempts = self.config.getint('Terminal', 'retry_attempts')
        
        self.log_dir = self.config.get('Paths', 'log_dir')
        self.data_dir = self.config.get('Paths', 'data_dir')
        self.temp_dir = self.config.get('Paths', 'temp_dir')
        
        self._ensure_directories()
        
        self.api_key = self._load_api_key()
    
    def _ensure_directories(self):
        """Create required directories"""
        for directory in [self.log_dir, self.data_dir, self.temp_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _load_api_key(self):
        """Load API key from secure storage"""
        token_file = os.path.join(self.data_dir, 'token.json')
        
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    return data.get('token')
            except Exception:
                pass
        
        return None
    
    def save_token(self, token):
        """
        Save API token
        
        Args:
            token: API authentication token
        """
        token_file = os.path.join(self.data_dir, 'token.json')
        
        with open(token_file, 'w') as f:
            json.dump({'token': token}, f)
        
        self.api_key = token
    
    def get(self, section, key, fallback=None):
        """
        Get configuration value
        
        Args:
            section: Configuration section
            key: Configuration key
            fallback: Default value if not found
            
        Returns:
            Configuration value
        """
        return self.config.get(section, key, fallback=fallback)
    
    def set(self, section, key, value):
        """
        Set configuration value
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = str(value)
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        
        self._load_config()
