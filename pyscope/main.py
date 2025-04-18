#!/usr/bin/env python3
"""
PyScope - Main application entry point.

This module serves as the entry point for the PyScope application. It initializes
the GUI and event listeners, handles command-line arguments, and manages the
application lifecycle.
"""

import sys
import os
import argparse
import logging
from PyQt5.QtWidgets import QApplication

from pyscope.magnifier_gui import MagnifierGUI
from pyscope import __version__


def setup_logging():
    """Configure the application logging."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.expanduser("~/.pyscope")
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, "pyscope.log"))
        ]
    )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PyScope - Screen Magnifier for Gamers")
    parser.add_argument('-v', '--version', action='version', version=f'PyScope {__version__}')
    parser.add_argument('-m', '--minimized', action='store_true', help='Start with the settings window minimized')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()


def main():
    """Application main entry point."""
    # Parse arguments first to check for debug mode
    args = parse_arguments()
    
    # Setup logging
    try:
        setup_logging()
        # Set debug level if requested
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Debug logging enabled")
    except Exception as e:
        # If logging setup fails, we'll continue without it
        print(f"Warning: Could not set up logging: {e}")
    
    # Log startup
    logging.info(f"Starting PyScope v{__version__}")
    
    # Initialize application
    app = QApplication(sys.argv)
    app.setApplicationName("PyScope")
    app.setApplicationVersion(__version__)
    
    # Set application style
    app.setStyle("Fusion")  # This provides a consistent look across platforms
    
    # Create and show GUI
    try:
        gui = MagnifierGUI()
        if not args.minimized:
            gui.show()
        
        # Start event loop
        exit_code = app.exec_()
        
        # Clean up and exit
        logging.info(f"PyScope shutting down with exit code {exit_code}")
        return exit_code
    
    except Exception as e:
        logging.error(f"Error starting PyScope: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
