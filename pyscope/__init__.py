"""
PyScope - A Python-based screen magnifier for gamers.

PyScope provides a customizable magnifying overlay for games and applications,
allowing precise targeting and detail viewing without compromising gameplay.
It uses platform-specific optimizations when available and offers a fallback
screen capture method for universal compatibility.

Features:
- Adjustable zoom levels with quick-toggle presets
- Circular or rectangular magnification window
- Customizable window size and position
- Global hotkeys for activation and zoom switching
- Position preview with offset overlay
- Persistent settings
"""

import os
import sys
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Force screen capture mode
USE_NATIVE_API = False

# Version information
__version__ = "0.1.0"
__author__ = "Kill_Me_I_Noobs"
__license__ = "MIT"
__status__ = "Alpha"  # Options: "Alpha", "Beta", "Production"

# Constants for the application
APP_NAME = "PyScope"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(APP_DIR, "resources")
USER_CONFIG_DIR = os.path.expanduser("~/.pyscope")

# Create a logger for the package
logger = logging.getLogger(__name__)

# Platform-specific settings
PLATFORM = platform.system()
IS_WINDOWS = PLATFORM == "Windows"
IS_MACOS = PLATFORM == "Darwin"
IS_LINUX = PLATFORM == "Linux"

# Environment variables
USE_NATIVE_API = IS_WINDOWS and not os.environ.get("PYSCOPE_NO_NATIVE", False)

# Feature flags
FULLSCREEN_SUPPORTED = False  # Explicitly mark fullscreen as unsupported

# Create resources directory if it doesn't exist and we're in development mode
if not os.path.exists(RESOURCES_DIR) and not getattr(sys, 'frozen', False):
    try:
        os.makedirs(RESOURCES_DIR, exist_ok=True)
    except OSError:
        logger.warning(f"Could not create resources directory at {RESOURCES_DIR}")

# Create user config directory if it doesn't exist
try:
    os.makedirs(USER_CONFIG_DIR, exist_ok=True)
except OSError:
    logger.warning(f"Could not create user config directory at {USER_CONFIG_DIR}")

def get_platform_info() -> Dict[str, Any]:
    """
    Get detailed information about the current platform.
    
    This is useful for debugging and logging.
    
    Returns:
        Dict[str, Any]: Platform information including OS, version, and Python version
    """
    info = {
        "os": PLATFORM,
        "python_version": platform.python_version(),
        "processor": platform.processor(),
    }
    
    # Add platform-specific details
    if IS_WINDOWS:
        info["windows_version"] = platform.version()
        info["windows_edition"] = platform.win32_edition() if hasattr(platform, 'win32_edition') else "Unknown"
    elif IS_MACOS:
        info["mac_version"] = platform.mac_ver()[0]
    elif IS_LINUX:
        info["linux_distribution"] = platform.freedesktop_os_release() if hasattr(platform, 'freedesktop_os_release') else "Unknown"
    
    return info

def check_dependencies() -> bool:
    """
    Verify that all required dependencies are available.
    
    Returns:
        bool: True if all dependencies are available, False otherwise
    """
    required_packages = ['PyQt5', 'pynput', 'mss', 'PIL']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        return False
    
    return True

# Import main classes for easier access - this should happen after all the initialization
try:
    from .magnifier import Magnifier
    from .magnifier_gui import MagnifierGUI
    
    # Ensure utils package is properly imported
    from . import utils
except ImportError as e:
    logger.error(f"Error importing PyScope modules: {e}")
    raise

# Print startup message in debug environments
if __debug__:
    logger.debug(f"PyScope {__version__} initialized")
    logger.debug(f"Platform: {PLATFORM}")
    logger.debug(f"Native API enabled: {USE_NATIVE_API}")
