"""
Settings management module for PyScope.

This module provides functionality for loading, saving, and managing application settings.
"""

import os
import json
import logging
from pathlib import Path


class Settings:
    """
    Handles application settings for PyScope.
    
    This class provides methods for saving and loading user preferences,
    with fallback to default values when settings are missing or invalid.
    """
    
    def __init__(self, settings_dir=None):
        """
        Initialize the settings manager.
        
        Args:
            settings_dir (str, optional): Directory to store settings file.
                If None, uses ~/.pyscope/ directory.
        """
        self.logger = logging.getLogger(__name__)
        
        # Determine settings directory and file
        if settings_dir is None:
            self.settings_dir = os.path.expanduser("~/.pyscope")
        else:
            self.settings_dir = settings_dir
            
        # Create directory if it doesn't exist
        os.makedirs(self.settings_dir, exist_ok=True)
        
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        
        # Define default settings
        self.default_settings = {
            "width": 400,
            "height": 400,
            "circular": True,
            "refresh_rate": 60,
            "x_offset": 0,
            "y_offset": 0,
            "toggle_mode": True,
            "hotkey_text": "X",
            "hotkey_is_mouse": False,
            "hotkey_mouse_button": None,
            "zoom_hotkey_text": "Z",
            "zoom_hotkey_is_mouse": False,
            "zoom_hotkey_mouse_button": None,
            "zoom_low": 2.0,
            "zoom_high": 4.0,
            "display_offset": False
        }
    
    def save_settings(self, settings):
        """
        Save settings to the settings file.
        
        Args:
            settings (dict): Settings to save
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Merge with defaults to ensure all settings are present
            merged_settings = self.default_settings.copy()
            merged_settings.update(settings)
            
            # Save to file
            with open(self.settings_file, 'w') as f:
                json.dump(merged_settings, f, indent=2)
                
            self.logger.info(f"Settings saved to {self.settings_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False
    
    def load_settings(self):
        """
        Load settings from the settings file.
        
        Returns:
            dict: Loaded settings or default settings if file doesn't exist or is invalid
        """
        try:
            # Check if file exists
            if not os.path.exists(self.settings_file):
                self.logger.info(f"Settings file not found at {self.settings_file}, using defaults")
                return self.default_settings
            
            # Load from file
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            # Validate settings
            validated_settings = self._validate_settings(settings)
            self.logger.info(f"Settings loaded from {self.settings_file}")
            return validated_settings
        
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in settings file {self.settings_file}, using defaults")
            return self.default_settings
        
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return self.default_settings
    
    def _validate_settings(self, settings):
        """
        Validate loaded settings and fill in missing values with defaults.
        
        Args:
            settings (dict): Settings to validate
        
        Returns:
            dict: Validated settings with default values for missing or invalid items
        """
        validated = {}
        
        # Copy all default settings first
        validated.update(self.default_settings)
        
        # Validate each setting
        for key, default_value in self.default_settings.items():
            if key in settings:
                value = settings[key]
                
                # Type checking based on default value type
                if isinstance(default_value, bool) and not isinstance(value, bool):
                    # Convert string 'True'/'False' to boolean
                    if isinstance(value, str):
                        validated[key] = value.lower() == 'true'
                    else:
                        validated[key] = bool(value)
                
                elif isinstance(default_value, int) and not isinstance(value, int):
                    try:
                        validated[key] = int(value)
                    except (ValueError, TypeError):
                        validated[key] = default_value
                
                elif isinstance(default_value, float) and not isinstance(value, float):
                    try:
                        validated[key] = float(value)
                    except (ValueError, TypeError):
                        validated[key] = default_value
                
                else:
                    validated[key] = value
        
        return validated
    
    def get_default(self, key):
        """
        Get a default setting value.
        
        Args:
            key (str): Setting key
        
        Returns:
            The default value for the setting, or None if it doesn't exist
        """
        return self.default_settings.get(key)
    
    def reset_to_defaults(self):
        """
        Reset all settings to default values.
        
        Returns:
            dict: Default settings
        """
        self.save_settings(self.default_settings)
        return self.default_settings.copy()
