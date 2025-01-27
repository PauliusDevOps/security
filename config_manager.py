from dataclasses import dataclass, asdict
import json
import os
from typing import Dict, Any, Optional
import yaml
from functools import wraps
import logging
from datetime import datetime

@dataclass
class SystemConfig:
    # GPIO Configuration
    DOOR_SENSOR_PIN: int = 16
    DOOR_LED_PIN: int = 17
    BUZZER_PIN: int = 12
    MOTION_SENSOR_PIN: int = 18
    MOTION_LED_PIN: int = 21
    
    # Timing Configuration
    BUZZER_INTERVAL: int = 3
    CAPTURE_INTERVAL: int = 5
    DISPLAY_UPDATE_INTERVAL: float = 0.5
    
    # Security Configuration
    LOGIN_ATTEMPTS_MAX: int = 5
    LOGIN_ATTEMPTS_WINDOW: int = 300
    SESSION_TIMEOUT: int = 3600
    
    # Storage Configuration
    IMAGE_DIR: str = 'static/captures'
    LOG_FILE: str = 'security_monitor.log'
    LOG_LEVEL: str = 'INFO'
    CONFIG_FILE: str = 'security_config.yaml'
    BACKUP_DIR: str = 'config_backups'
    
    # Image and Video Configuration
    IMAGE_RESOLUTION: tuple = (640, 480)
    IMAGE_QUALITY: int = 85
    MOTION_DETECTION_SENSITIVITY: int = 50
    
    # Notification Configuration
    ENABLE_EMAIL_NOTIFICATIONS: bool = False
    NOTIFICATION_EMAIL: str = ''
    SMTP_SERVER: str = ''
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ''
    SMTP_PASSWORD: str = ''

class ConfigurationManager:
    def __init__(self, config_file: str = 'security_config.yaml'):
        self.config_file = config_file
        self.config = SystemConfig()
        self.logger = logging.getLogger('SecurityMonitor')
        self._load_config()
        
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if config_data:
                        for key, value in config_data.items():
                            if hasattr(self.config, key):
                                setattr(self.config, key, value)
                self.logger.info("Configuration loaded successfully")
            else:
                self._save_config()  # Create default config file
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            
    def _save_config(self) -> None:
        """Save current configuration to YAML file"""
        try:
            # Create backup directory if it doesn't exist
            os.makedirs(self.config.BACKUP_DIR, exist_ok=True)
            
            # Create backup of current config if it exists
            if os.path.exists(self.config_file):
                backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = os.path.join(
                    self.config.BACKUP_DIR, 
                    f'config_backup_{backup_time}.yaml'
                )
                os.rename(self.config_file, backup_file)
            
            # Save new configuration
            with open(self.config_file, 'w') as f:
                yaml.dump(asdict(self.config), f, default_flow_style=False)
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            
    def update_config(self, updates: Dict[str, Any]) -> tuple[bool, str]:
        """Update configuration with validation"""
        try:
            # Validate updates
            for key, value in updates.items():
                if not hasattr(self.config, key):
                    return False, f"Invalid configuration key: {key}"
                
                # Type validation
                expected_type = type(getattr(self.config, key))
                if not isinstance(value, expected_type):
                    try:
                        # Attempt type conversion
                        updates[key] = expected_type(value)
                    except (ValueError, TypeError):
                        return False, f"Invalid type for {key}: expected {expected_type.__name__}"
                
                # Value validation
                if not self._validate_value(key, updates[key]):
                    return False, f"Invalid value for {key}"
            
            # Apply updates
            for key, value in updates.items():
                setattr(self.config, key, value)
            
            # Save updated configuration
            self._save_config()
            return True, "Configuration updated successfully"
        except Exception as e:
            return False, f"Error updating configuration: {str(e)}"
    
    def _validate_value(self, key: str, value: Any) -> bool:
        """Validate configuration values"""
        try:
            # PIN validation
            if key.endswith('_PIN'):
                return 0 <= value <= 27  # Valid GPIO pins on Raspberry Pi
            
            # Interval validation
            if key.endswith('_INTERVAL'):
                return value > 0
            
            # Path validation
            if key.endswith('_DIR'):
                return isinstance(value, str) and len(value) > 0
            
            # Port validation
            if key.endswith('_PORT'):
                return 0 <= value <= 65535
            
            # Quality validation
            if key == 'IMAGE_QUALITY':
                return 0 <= value <= 100
            
            # Sensitivity validation
            if key == 'MOTION_DETECTION_SENSITIVITY':
                return 0 <= value <= 100
            
            # Email validation
            if key == 'NOTIFICATION_EMAIL':
                return '@' in value if value else True
            
            return True
        except Exception:
            return False
            
    def get_config(self) -> SystemConfig:
        """Get current configuration"""
        return self.config
    
    def restore_backup(self, backup_file: str) -> tuple[bool, str]:
        """Restore configuration from backup"""
        try:
            backup_path = os.path.join(self.config.BACKUP_DIR, backup_file)
            if not os.path.exists(backup_path):
                return False, "Backup file not found"
            
            with open(backup_path, 'r') as f:
                backup_data = yaml.safe_load(f)
            
            success, message = self.update_config(backup_data)
            if success:
                return True, "Configuration restored successfully"
            return False, f"Error restoring configuration: {message}"
        except Exception as e:
            return False, f"Error restoring backup: {str(e)}"
    
    def list_backups(self) -> list[str]:
        """List available configuration backups"""
        try:
            if not os.path.exists(self.config.BACKUP_DIR):
                return []
            return [f for f in os.listdir(self.config.BACKUP_DIR) 
                   if f.startswith('config_backup_') and f.endswith('.yaml')]
        except Exception:
            return []