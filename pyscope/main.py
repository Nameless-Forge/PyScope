#!/usr/bin/env python3
"""
PyScope - Main application entry point.

This module serves as the entry point for the PyScope application. It initializes
the GUI and event listeners, handles command-line arguments, and manages the
application lifecycle.

PyScope is a Python-based screen magnifier designed specifically for gamers,
providing customizable zoom overlays to enhance targeting and visibility
without compromising gameplay performance.
"""

import sys
import os
import platform
import argparse
import logging
import traceback
import importlib.resources
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

# Import local modules
from pyscope.magnifier_gui import MagnifierGUI
from pyscope import __version__


# Constants for the application
APP_NAME = "PyScope"
LOG_DIR = os.path.expanduser("~/.pyscope")
CONFIG_DIR = LOG_DIR  # Using same directory for logs and config
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pyscope", "resources")


def setup_logging(debug=False):
    """
    Configure the application logging system.
    
    Creates log directories and sets up file and console handlers with
    appropriate formatting. Debug mode enables more verbose logging.
    
    Args:
        debug (bool): Whether to enable debug logging level
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Set the default log level
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure the root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(LOG_DIR, "pyscope.log"))
        ]
    )
    
    # Log the startup information
    logging.info(f"Starting {APP_NAME} v{__version__}")
    logging.info(f"Platform: {platform.system()} {platform.version()}")
    logging.info(f"Python version: {platform.python_version()}")
    
    if debug:
        logging.debug("Debug logging enabled")


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: The parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - A screen magnifier specifically designed for gamers",
        epilog="Note: Fullscreen mode is not supported in games."
    )
    
    parser.add_argument('-v', '--version', action='version', 
                       version=f'{APP_NAME} {__version__}')
    
    parser.add_argument('-m', '--minimized', action='store_true', 
                       help='Start with the settings window minimized')
    
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug logging')
                       
    parser.add_argument('--no-native', action='store_true',
                       help='Disable Windows Magnification API (forces screen capture mode)')
    
    parser.add_argument('--reset-config', action='store_true',
                       help='Reset all settings to defaults on startup')
    
    return parser.parse_args()


def check_system_requirements():
    """
    Check if the current system meets the requirements.
    
    Returns:
        bool: True if all requirements are met, False otherwise
    """
    system = platform.system()
    
    # Log system information
    logging.info(f"Checking system requirements for {system}")
    
    # Check Python version (require 3.7+)
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 7):
        logging.error(f"Python 3.7+ required, found {python_version.major}.{python_version.minor}")
        return False
    
    # Windows-specific checks
    if system == "Windows":
        # Check if we're on Windows 10/11 for best magnification API support
        win_version = platform.version().split('.')
        if len(win_version) >= 2:
            major = int(win_version[0]) if win_version[0].isdigit() else 0
            if major < 10:
                logging.warning("Windows 10 or later recommended for best performance")
    
    # Linux-specific checks
    elif system == "Linux":
        # Check for X11 (for screen capturing)
        if "DISPLAY" not in os.environ:
            logging.error("X11 display server required")
            return False
    
    # MacOS-specific checks
    elif system == "Darwin":
        # Just log for now, specific macOS requirements can be added later
        logging.info("Running on macOS")
    
    return True


def show_startup_error(title, message):
    """
    Display an error message dialog for critical startup errors.
    
    Args:
        title (str): The dialog title
        message (str): The error message to display
    """
    # Create a minimal application if needed
    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    
    # Show error dialog
    error_box = QMessageBox()
    error_box.setIcon(QMessageBox.Critical)
    error_box.setWindowTitle(title)
    error_box.setText(message)
    error_box.exec_()


def initialize_app_environment():
    """
    Set up the application environment.
    
    This includes creating necessary directories and setting environment variables.
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    try:
        # Create config directory if it doesn't exist
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Create resources directory if it doesn't exist and it's not a packaged app
        if not os.path.exists(RESOURCES_DIR) and not hasattr(sys, 'frozen'):
            os.makedirs(RESOURCES_DIR, exist_ok=True)
        
        # Set environment variables
        if platform.system() == "Windows":
            # Set process DPI awareness to improve display on high-DPI screens
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Per-monitor DPI awareness
            except Exception as e:
                logging.warning(f"Could not set DPI awareness: {e}")
        
        return True
    
    except Exception as e:
        logging.error(f"Failed to initialize app environment: {e}")
        return False


def get_splash_screen():
    """
    Create a splash screen for application startup.
    
    Returns:
        QSplashScreen or None: The splash screen if created successfully, None otherwise
    """
    try:
        # Try to find the splash image
        splash_path = os.path.join(RESOURCES_DIR, "splash.png")
        
        if os.path.exists(splash_path):
            pixmap = QPixmap(splash_path)
            splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
            splash.setWindowFlag(Qt.FramelessWindowHint)
            splash.showMessage(f"Starting {APP_NAME} v{__version__}", 
                              Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            return splash
    except Exception as e:
        logging.warning(f"Could not create splash screen: {e}")
    
    return None


def main():
    """
    Application main entry point.
    
    This function initializes the application, creates the GUI, and
    starts the event loop.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    # Parse arguments first to check for debug mode
    args = parse_arguments()
    
    # Set up logging with debug flag from arguments
    try:
        setup_logging(args.debug)
    except Exception as e:
        print(f"Warning: Could not set up logging: {e}")
    
    # Check system requirements
    if not check_system_requirements():
        error_msg = "Your system does not meet the minimum requirements for PyScope."
        logging.error(error_msg)
        show_startup_error("System Requirements Error", error_msg)
        return 1
    
    # Initialize application environment
    if not initialize_app_environment():
        error_msg = "Failed to initialize application environment."
        logging.error(error_msg)
        show_startup_error("Initialization Error", error_msg)
        return 1
    
    # Initialize application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    
    # Set application style
    app.setStyle("Fusion")  # This provides a consistent look across platforms
    
    # Show splash screen if available
    splash = get_splash_screen()
    if splash:
        splash.show()
        app.processEvents()
    
    # Create and show GUI
    try:
        # Add environment variable for native API if requested
        if args.no_native:
            os.environ["PYSCOPE_NO_NATIVE"] = "1"
            logging.info("Native Windows Magnification API disabled via command line")
        
        # Create GUI with a slight delay to allow splash screen to show
        def create_gui():
            try:
                gui = MagnifierGUI()
                
                # Reset config if requested
                if args.reset_config and hasattr(gui, 'settings'):
                    gui.settings.reset_to_defaults()
                    gui.load_settings()
                    gui.apply_settings()
                    logging.info("Settings reset to defaults")
                
                # Show GUI unless minimized flag is set
                if not args.minimized:
                    gui.show()
                
                # Hide splash screen if it was shown
                if splash:
                    splash.finish(gui)
                
            except Exception as e:
                logging.error(f"Error creating GUI: {e}", exc_info=True)
                if splash:
                    splash.finish(None)
                show_startup_error("Startup Error", f"Error starting {APP_NAME}:\n{str(e)}")
                app.quit()
        
        # Use a short timer to allow the splash screen to appear
        if splash:
            QTimer.singleShot(500, create_gui)
        else:
            create_gui()
        
        # Start event loop
        exit_code = app.exec_()
        
        # Clean up and exit
        logging.info(f"{APP_NAME} shutting down with exit code {exit_code}")
        return exit_code
    
    except Exception as e:
        # Get detailed traceback
        tb = traceback.format_exc()
        logging.error(f"Error starting {APP_NAME}: {e}\n{tb}")
        
        # Show error dialog
        error_message = f"An unexpected error occurred while starting {APP_NAME}:\n\n{str(e)}"
        show_startup_error("Startup Error", error_message)
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
