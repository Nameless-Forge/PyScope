import sys
import os
import json
import logging
import platform
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QLineEdit, QCheckBox, QRadioButton, QButtonGroup,
    QPushButton, QGridLayout, QGroupBox, QMessageBox, QStatusBar
)
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

from .magnifier import Magnifier
from .utils.overlay import OffsetOverlay
from .utils.settings import Settings

# Set up logger
logger = logging.getLogger(__name__)

class MagnifierGUI(QMainWindow):
    """GUI for controlling the PyScope screen magnifier."""
    
    def __init__(self):
        super().__init__()
        # Initialize core components
        self.magnifier = Magnifier()
        self.initialize_magnifier()
        
        # Setup keyboard/mouse listeners
        self.key_listener = None
        self.mouse_listener = None
        self.hotkey_capture_active = False
        self.zoom_hotkey_capture_active = False
        
        # Hotkey settings
        self.hotkey = KeyCode.from_char('x')
        self.hotkey_is_mouse = False
        self.hotkey_mouse_button = None
        self.zoom_hotkey = KeyCode.from_char('z')
        self.zoom_hotkey_is_mouse = False 
        self.zoom_hotkey_mouse_button = None
        
        # Activation mode
        self.toggle_mode = True  # True for toggle, False for hold
        
        # Internal state
        self.window_visible = False
        self.offset_overlay = None
        self.settings = Settings()
        
        # Initialize UI
        self.init_ui()
        self.setup_keyboard_listeners()
        
        # Load settings
        self.load_settings()
        self.apply_settings()
        
        # Set window properties
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #2b2b2b;")
        
        # Display status message about the magnifier mode
        self.update_status_message()
    
    def initialize_magnifier(self):
        """Initialize the magnifier and handle any errors."""
        success = self.magnifier.initialize()
        if not success:
            QMessageBox.warning(
                self, 
                "Initialization Warning",
                "Could not fully initialize the magnifier. Some features may be limited.",
                QMessageBox.Ok
            )
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PyScope Settings")
        
        # Try to load icon if available
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("PyScope")
        title_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        
        tip_label = QLabel("Toggle this menu (INSERT)")
        tip_label.setStyleSheet("color: #aaaaaa; font-size: 16px;")
        tip_label.setAlignment(Qt.AlignCenter)
        
        # Add warning for fullscreen mode
        warning_label = QLabel("⚠️ FULLSCREEN NOT SUPPORTED ⚠️")
        warning_label.setStyleSheet("color: #ff7777; font-size: 14px; font-weight: bold;")
        warning_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(tip_label)
        header_layout.addWidget(warning_label)
        main_layout.addWidget(header_widget)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        
        # Hotkey settings
        self.create_hotkey_group(content_layout)
        
        # Window settings
        self.create_window_settings_group(content_layout)
        
        # Zoom settings
        self.create_zoom_settings_group(content_layout)
        
        # API mode display (only on Windows)
        if platform.system() == "Windows":
            self.create_api_mode_group(content_layout)
        
        main_layout.addWidget(content_widget)
        
        # Create button panel
        button_panel = QWidget()
        button_layout = QHBoxLayout(button_panel)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        apply_button = QPushButton("Apply Settings")
        apply_button.setStyleSheet("background-color: #3d3d3d; color: white; padding: 8px 16px;")
        apply_button.clicked.connect(self.on_apply_settings)
        
        reset_button = QPushButton("Reset Defaults")
        reset_button.setStyleSheet("background-color: #3d3d3d; color: white; padding: 8px 16px;")
        reset_button.clicked.connect(self.on_reset_defaults)
        
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("background-color: #3d3d3d; color: white; padding: 8px 16px;")
        exit_button.clicked.connect(self.on_exit)
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(exit_button)
        
        main_layout.addWidget(button_panel)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #aaaaaa;")
        main_layout.addWidget(self.status_bar)
        
        # Set size
        self.setMinimumWidth(430)
        self.setFixedSize(self.sizeHint())
    
    def create_api_mode_group(self, parent_layout):
        """Create a group to display the API mode (Windows only)."""
        api_group = QGroupBox("Magnification Engine")
        api_group.setStyleSheet("QGroupBox { color: white; border: 1px solid gray; margin-top: 1ex; } "
                                "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }")
        api_layout = QVBoxLayout(api_group)
        
        # Create label to display the API mode
        self.api_mode_label = QLabel("")
        
        # Set the text based on the current magnifier state
        if hasattr(self.magnifier, 'use_native_api'):
            if self.magnifier.use_native_api:
                self.api_mode_label.setText("Using Windows Magnification API (Best Performance)")
                self.api_mode_label.setStyleSheet("color: #88ff88;")  # Green for good
            else:
                self.api_mode_label.setText("Using Screen Capture (Compatibility Mode)")
                self.api_mode_label.setStyleSheet("color: #ffaa44;")  # Orange for warning
        else:
            self.api_mode_label.setText("Unknown API Mode")
            self.api_mode_label.setStyleSheet("color: #ff7777;")  # Red for error
        
        self.api_mode_label.setAlignment(Qt.AlignCenter)
        api_layout.addWidget(self.api_mode_label)
        
        parent_layout.addWidget(api_group)
    
    def create_hotkey_group(self, parent_layout):
        """Create hotkey settings group."""
        hotkey_group = QGroupBox("Hotkey (Toggle/Hold)")
        hotkey_group.setStyleSheet("QGroupBox { color: white; border: 1px solid gray; margin-top: 1ex; } "
                                 "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }")
        hotkey_layout = QGridLayout(hotkey_group)
        
        # Hotkey input
        hotkey_label = QLabel("Press a key:")
        hotkey_label.setStyleSheet("color: white;")
        self.hotkey_input = QLineEdit("X")
        self.hotkey_input.setReadOnly(True)
        self.hotkey_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        self.hotkey_input.mousePressEvent = self.on_hotkey_input_click
        
        # Radio buttons for toggle/hold
        self.toggle_radio = QRadioButton("Toggle")
        self.toggle_radio.setStyleSheet("color: white;")
        self.toggle_radio.setChecked(True)
        
        self.hold_radio = QRadioButton("Hold")
        self.hold_radio.setStyleSheet("color: white;")
        
        # Add to layout
        hotkey_layout.addWidget(hotkey_label, 0, 0)
        hotkey_layout.addWidget(self.hotkey_input, 0, 1)
        hotkey_layout.addWidget(self.toggle_radio, 1, 0)
        hotkey_layout.addWidget(self.hold_radio, 1, 1)
        
        parent_layout.addWidget(hotkey_group)
    
    def create_window_settings_group(self, parent_layout):
        """Create window settings group."""
        settings_group = QGroupBox("Window Settings")
        settings_group.setStyleSheet("QGroupBox { color: white; border: 1px solid gray; margin-top: 1ex; } "
                                   "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }")
        settings_layout = QGridLayout(settings_group)
        
        # Width setting
        width_label = QLabel("Width:")
        width_label.setStyleSheet("color: white;")
        
        self.width_input = QLineEdit("400")
        self.width_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(100, 2000)
        self.width_slider.setValue(400)
        self.width_slider.setStyleSheet("QSlider::groove:horizontal { background: #555555; height: 8px; border-radius: 4px; }"
                                       "QSlider::handle:horizontal { background: #888888; width: 18px; margin: -5px 0; border-radius: 9px; }")
        self.width_slider.valueChanged.connect(lambda v: self.width_input.setText(str(v)))
        
        # Height setting
        height_label = QLabel("Height:")
        height_label.setStyleSheet("color: white;")
        
        self.height_input = QLineEdit("400")
        self.height_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        self.height_slider = QSlider(Qt.Horizontal)
        self.height_slider.setRange(100, 2000)
        self.height_slider.setValue(400)
        self.height_slider.setStyleSheet("QSlider::groove:horizontal { background: #555555; height: 8px; border-radius: 4px; }"
                                        "QSlider::handle:horizontal { background: #888888; width: 18px; margin: -5px 0; border-radius: 9px; }")
        self.height_slider.valueChanged.connect(lambda v: self.height_input.setText(str(v)))
        
        # Circular shape
        circular_label = QLabel("Circular Shape:")
        circular_label.setStyleSheet("color: white;")
        
        self.circular_checkbox = QCheckBox()
        self.circular_checkbox.setChecked(True)
        self.circular_checkbox.setStyleSheet("QCheckBox::indicator { width: 15px; height: 15px; }"
                                           "QCheckBox::indicator:unchecked { background-color: #3d3d3d; border: 1px solid gray; }"
                                           "QCheckBox::indicator:checked { background-color: #4d8bf0; border: 1px solid gray; }")
        
        # Display offset
        offset_display_label = QLabel("Display Offset:")
        offset_display_label.setStyleSheet("color: white;")
        
        self.offset_display_checkbox = QCheckBox()
        self.offset_display_checkbox.setChecked(False)
        self.offset_display_checkbox.setStyleSheet("QCheckBox::indicator { width: 15px; height: 15px; }"
                                                 "QCheckBox::indicator:unchecked { background-color: #3d3d3d; border: 1px solid gray; }"
                                                 "QCheckBox::indicator:checked { background-color: #4d8bf0; border: 1px solid gray; }")
        
        # Refresh rate setting
        refresh_label = QLabel("Refresh Rate (FPS):")
        refresh_label.setStyleSheet("color: white;")
        
        self.refresh_input = QLineEdit("60")
        self.refresh_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        self.refresh_slider = QSlider(Qt.Horizontal)
        self.refresh_slider.setRange(1, 144)
        self.refresh_slider.setValue(60)
        self.refresh_slider.setStyleSheet("QSlider::groove:horizontal { background: #555555; height: 8px; border-radius: 4px; }"
                                        "QSlider::handle:horizontal { background: #888888; width: 18px; margin: -5px 0; border-radius: 9px; }")
        self.refresh_slider.valueChanged.connect(lambda v: self.refresh_input.setText(str(v)))
        
        # X offset setting
        x_offset_label = QLabel("Offset X:")
        x_offset_label.setStyleSheet("color: white;")
        
        self.x_offset_input = QLineEdit("0")
        self.x_offset_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        self.x_offset_slider = QSlider(Qt.Horizontal)
        self.x_offset_slider.setRange(-200, 200)  # Increased range from -100,100
        self.x_offset_slider.setValue(0)
        self.x_offset_slider.setStyleSheet("QSlider::groove:horizontal { background: #555555; height: 8px; border-radius: 4px; }"
                                         "QSlider::handle:horizontal { background: #888888; width: 18px; margin: -5px 0; border-radius: 9px; }")
        self.x_offset_slider.valueChanged.connect(lambda v: self.x_offset_input.setText(str(v)))
        
        # Y offset setting
        y_offset_label = QLabel("Offset Y:")
        y_offset_label.setStyleSheet("color: white;")
        
        self.y_offset_input = QLineEdit("0")
        self.y_offset_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        self.y_offset_slider = QSlider(Qt.Horizontal)
        self.y_offset_slider.setRange(-200, 200)  # Increased range from -100,100
        self.y_offset_slider.setValue(0)
        self.y_offset_slider.setStyleSheet("QSlider::groove:horizontal { background: #555555; height: 8px; border-radius: 4px; }"
                                         "QSlider::handle:horizontal { background: #888888; width: 18px; margin: -5px 0; border-radius: 9px; }")
        self.y_offset_slider.valueChanged.connect(lambda v: self.y_offset_input.setText(str(v)))
        
        # Add to layout
        settings_layout.addWidget(width_label, 0, 0)
        settings_layout.addWidget(self.width_input, 0, 1)
        settings_layout.addWidget(self.width_slider, 0, 2)
        
        settings_layout.addWidget(height_label, 1, 0)
        settings_layout.addWidget(self.height_input, 1, 1)
        settings_layout.addWidget(self.height_slider, 1, 2)
        
        settings_layout.addWidget(circular_label, 2, 0)
        settings_layout.addWidget(self.circular_checkbox, 2, 1)
        
        settings_layout.addWidget(offset_display_label, 3, 0)
        settings_layout.addWidget(self.offset_display_checkbox, 3, 1)
        
        settings_layout.addWidget(refresh_label, 4, 0)
        settings_layout.addWidget(self.refresh_input, 4, 1)
        settings_layout.addWidget(self.refresh_slider, 4, 2)
        
        settings_layout.addWidget(x_offset_label, 5, 0)
        settings_layout.addWidget(self.x_offset_input, 5, 1)
        settings_layout.addWidget(self.x_offset_slider, 5, 2)
        
        settings_layout.addWidget(y_offset_label, 6, 0)
        settings_layout.addWidget(self.y_offset_input, 6, 1)
        settings_layout.addWidget(self.y_offset_slider, 6, 2)
        
        parent_layout.addWidget(settings_group)
    
    def create_zoom_settings_group(self, parent_layout):
        """Create zoom settings group."""
        zoom_group = QGroupBox("Zoom Multiplier Settings")
        zoom_group.setStyleSheet("QGroupBox { color: white; border: 1px solid gray; margin-top: 1ex; } "
                               "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }")
        zoom_layout = QGridLayout(zoom_group)
        
        # Zoom hotkey
        zoom_hotkey_label = QLabel("Hotkey:")
        zoom_hotkey_label.setStyleSheet("color: white;")
        
        self.zoom_hotkey_input = QLineEdit("Z")
        self.zoom_hotkey_input.setReadOnly(True)
        self.zoom_hotkey_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        self.zoom_hotkey_input.mousePressEvent = self.on_zoom_hotkey_input_click
        
        # Zoom low setting
        zoom_low_label = QLabel("Zoom value 1:")
        zoom_low_label.setStyleSheet("color: white;")
        
        self.zoom_low_input = QLineEdit("2.0")
        self.zoom_low_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        # Zoom high setting
        zoom_high_label = QLabel("Zoom value 2:")
        zoom_high_label.setStyleSheet("color: white;")
        
        self.zoom_high_input = QLineEdit("4.0")
        self.zoom_high_input.setStyleSheet("background-color: #3d3d3d; color: white; padding: 5px;")
        
        # Add to layout
        zoom_layout.addWidget(zoom_hotkey_label, 0, 0)
        zoom_layout.addWidget(self.zoom_hotkey_input, 0, 1)
        
        zoom_layout.addWidget(zoom_low_label, 1, 0)
        zoom_layout.addWidget(self.zoom_low_input, 1, 1)
        
        zoom_layout.addWidget(zoom_high_label, 2, 0)
        zoom_layout.addWidget(self.zoom_high_input, 2, 1)
        
        parent_layout.addWidget(zoom_group)
    
    def on_hotkey_input_click(self, event):
        """Handle clicks on the hotkey input field."""
        self.hotkey_input.setText("Press a key...")
        self.hotkey_capture_active = True
        
    def on_zoom_hotkey_input_click(self, event):
        """Handle clicks on the zoom hotkey input field."""
        self.zoom_hotkey_input.setText("Press a key...")
        self.zoom_hotkey_capture_active = True
    
    def on_apply_settings(self):
        """Handle apply settings button click."""
        self.save_settings()
        self.apply_settings()
        self.status_bar.showMessage("Settings applied successfully", 3000)
    
    def on_reset_defaults(self):
        """Reset all settings to default values."""
        result = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # Reset using settings manager
            default_settings = self.settings.reset_to_defaults()
            
            # Update UI with default values
            self.width_input.setText(str(default_settings["width"]))
            self.width_slider.setValue(default_settings["width"])
            
            self.height_input.setText(str(default_settings["height"]))
            self.height_slider.setValue(default_settings["height"])
            
            self.circular_checkbox.setChecked(default_settings["circular"])
            
            self.refresh_input.setText(str(default_settings["refresh_rate"]))
            self.refresh_slider.setValue(default_settings["refresh_rate"])
            
            self.x_offset_input.setText(str(default_settings["x_offset"]))
            self.x_offset_slider.setValue(default_settings["x_offset"])
            
            self.y_offset_input.setText(str(default_settings["y_offset"]))
            self.y_offset_slider.setValue(default_settings["y_offset"])
            
            self.toggle_radio.setChecked(default_settings["toggle_mode"])
            self.hold_radio.setChecked(not default_settings["toggle_mode"])
            
            self.hotkey_input.setText(default_settings["hotkey_text"])
            self.hotkey_is_mouse = default_settings["hotkey_is_mouse"]
            
            self.zoom_hotkey_input.setText(default_settings["zoom_hotkey_text"])
            self.zoom_hotkey_is_mouse = default_settings["zoom_hotkey_is_mouse"]
            
            self.zoom_low_input.setText(str(default_settings["zoom_low"]))
            self.zoom_high_input.setText(str(default_settings["zoom_high"]))
            
            self.offset_display_checkbox.setChecked(default_settings["display_offset"])
            
            # Apply settings
            self.apply_settings()
            
            self.status_bar.showMessage("Settings reset to defaults", 3000)
    
    def on_exit(self):
        """Handle exit button click."""
        # Clean up
        self.save_settings()
        self.magnifier.dispose()
        
        # Close listeners
        if self.key_listener:
            self.key_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        # Exit application
        QApplication.quit()
    
    def update_status_message(self):
        """Update the status bar with information about the current magnifier mode."""
        if hasattr(self.magnifier, 'use_native_api'):
            if self.magnifier.use_native_api:
                self.status_bar.showMessage("Using Windows Magnification API for best performance")
            else:
                self.status_bar.showMessage("Using screen capture mode")
        else:
            self.status_bar.showMessage("Ready")
    
    def save_settings(self):
        """Save settings to file."""
        try:
            settings = {
                "width": int(self.width_input.text()),
                "height": int(self.height_input.text()),
                "circular": self.circular_checkbox.isChecked(),
                "refresh_rate": int(self.refresh_input.text()),
                "x_offset": int(self.x_offset_input.text()),
                "y_offset": int(self.y_offset_input.text()),
                "toggle_mode": self.toggle_radio.isChecked(),
                "hotkey_text": self.hotkey_input.text(),
                "hotkey_is_mouse": self.hotkey_is_mouse,
                "hotkey_mouse_button": self.hotkey_mouse_button.name if self.hotkey_is_mouse and self.hotkey_mouse_button else None,
                "zoom_hotkey_text": self.zoom_hotkey_input.text(),
                "zoom_hotkey_is_mouse": self.zoom_hotkey_is_mouse,
                "zoom_hotkey_mouse_button": self.zoom_hotkey_mouse_button.name if self.zoom_hotkey_is_mouse and self.zoom_hotkey_mouse_button else None,
                "zoom_low": float(self.zoom_low_input.text()),
                "zoom_high": float(self.zoom_high_input.text()),
                "display_offset": self.offset_display_checkbox.isChecked()
            }
            
            # Save using settings manager
            self.settings.save_settings(settings)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.warning(
                self,
                "Save Error",
                f"Could not save settings: {str(e)}",
                QMessageBox.Ok
            )
    
    def load_settings(self):
        """Load settings from file."""
        settings = self.settings.load_settings()
        if not settings:
            logger.warning("No settings found, using defaults")
            return
        
        try:
            # Apply to UI
            self.width_input.setText(str(settings.get("width", 400)))
            self.width_slider.setValue(int(settings.get("width", 400)))
            
            self.height_input.setText(str(settings.get("height", 400)))
            self.height_slider.setValue(int(settings.get("height", 400)))
            
            self.circular_checkbox.setChecked(settings.get("circular", True))
            
            self.refresh_input.setText(str(settings.get("refresh_rate", 60)))
            self.refresh_slider.setValue(int(settings.get("refresh_rate", 60)))
            
            self.x_offset_input.setText(str(settings.get("x_offset", 0)))
            self.x_offset_slider.setValue(int(settings.get("x_offset", 0)))
            
            self.y_offset_input.setText(str(settings.get("y_offset", 0)))
            self.y_offset_slider.setValue(int(settings.get("y_offset", 0)))
            
            self.toggle_radio.setChecked(settings.get("toggle_mode", True))
            self.hold_radio.setChecked(not settings.get("toggle_mode", True))
            
            self.hotkey_input.setText(settings.get("hotkey_text", "X"))
            self.hotkey_is_mouse = settings.get("hotkey_is_mouse", False)
            
            self.zoom_hotkey_input.setText(settings.get("zoom_hotkey_text", "Z"))
            self.zoom_hotkey_is_mouse = settings.get("zoom_hotkey_is_mouse", False)
            
            self.zoom_low_input.setText(str(settings.get("zoom_low", 2.0)))
            self.zoom_high_input.setText(str(settings.get("zoom_high", 4.0)))
            
            self.offset_display_checkbox.setChecked(settings.get("display_offset", False))
            
            # Load hotkey settings
            if self.hotkey_is_mouse:
                button_name = settings.get("hotkey_mouse_button")
                if button_name:
                    try:
                        self.hotkey_mouse_button = getattr(Button, button_name)
                    except AttributeError:
                        logger.warning(f"Mouse button '{button_name}' not found, using defaults")
                        self.hotkey_is_mouse = False
            else:
                self.hotkey = self.key_from_string(settings.get("hotkey_text", "x"))
            
            # Load zoom hotkey settings
            if self.zoom_hotkey_is_mouse:
                button_name = settings.get("zoom_hotkey_mouse_button")
                if button_name:
                    try:
                        self.zoom_hotkey_mouse_button = getattr(Button, button_name)
                    except AttributeError:
                        logger.warning(f"Mouse button '{button_name}' not found, using defaults")
                        self.zoom_hotkey_is_mouse = False
            else:
                self.zoom_hotkey = self.key_from_string(settings.get("zoom_hotkey_text", "z"))
                
            logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            QMessageBox.warning(
                self,
                "Load Error",
                f"Could not load settings: {str(e)}",
                QMessageBox.Ok
            )
    
    def key_from_string(self, key_str):
        """
        Convert a key string to a pynput.keyboard.Key or KeyCode.
        
        Args:
            key_str (str): String representation of the key
            
        Returns:
            Key or KeyCode: The key object
        """
        # Handle special keys
        if key_str.lower() == "insert":
            return Key.insert
            
        # Dictionary of common key mappings
        key_map = {
            "space": Key.space,
            "tab": Key.tab,
            "enter": Key.enter,
            "return": Key.enter,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "esc": Key.esc,
            "escape": Key.esc,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
            "home": Key.home,
            "end": Key.end,
            "page up": Key.page_up,
            "page down": Key.page_down,
            "shift": Key.shift,
            "ctrl": Key.ctrl,
            "control": Key.ctrl,
            "alt": Key.alt,
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12
        }
        
        # Check key map
        if key_str.lower() in key_map:
            return key_map[key_str.lower()]
        
        # Check direct key attributes
        for key in vars(Key):
            if not key.startswith('_') and key_str.lower() == key:
                return getattr(Key, key)
        
        # Single character keys
        if len(key_str) == 1:
            return KeyCode.from_char(key_str.lower())
        
        # Default
        logger.warning(f"Unknown key '{key_str}', defaulting to 'x'")
        return KeyCode.from_char('x')
    
    def apply_settings(self):
        """Apply current settings to the magnifier."""
        try:
            # Get values from inputs
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            refresh_rate = int(self.refresh_input.text())
            x_offset = int(self.x_offset_input.text())
            y_offset = int(self.y_offset_input.text())
            circular = self.circular_checkbox.isChecked()
            display_offset = self.offset_display_checkbox.isChecked()
            zoom_low = float(self.zoom_low_input.text())
            zoom_high = float(self.zoom_high_input.text())
            
            # Apply to magnifier
            self.magnifier.set_resolution(width, height)
            self.magnifier.set_window_shape(circular)
            self.magnifier.set_refresh_rate(refresh_rate)
            self.magnifier.move_window(x_offset, y_offset)
            
            # Update zoom settings
            self.magnifier.zoom_level_low = zoom_low
            self.magnifier.zoom_level_high = zoom_high
            
            # Update activation mode
            self.toggle_mode = self.toggle_radio.isChecked()
            
            # Handle offset display
            if display_offset:
                if self.magnifier.is_visible():
                    self.magnifier.hide_window()
                
                if not self.offset_overlay:
                    from .utils.overlay import OffsetOverlay
                    self.offset_overlay = OffsetOverlay(width, height, x_offset, y_offset, circular)
                else:
                    self.offset_overlay.update_settings(width, height, x_offset, y_offset, circular)
                
                if self.window_visible:
                    self.offset_overlay.show()
            else:
                if self.offset_overlay and self.offset_overlay.isVisible():
                    self.offset_overlay.hide()
                    
            logger.info("Settings applied successfully")
        
        except ValueError as e:
            error_message = f"Invalid setting value: {e}"
            logger.error(error_message)
            QMessageBox.warning(
                self,
                "Input Error",
                error_message,
                QMessageBox.Ok
            )
        except Exception as e:
            error_message = f"Error applying settings: {e}"
            logger.error(error_message)
            QMessageBox.warning(
                self,
                "Error",
                error_message,
                QMessageBox.Ok
            )
    
    def setup_keyboard_listeners(self):
        """Setup keyboard and mouse event listeners for global hotkeys."""
        def on_key_press(key):
            # Capture hotkey for settings
            if self.hotkey_capture_active:
                self.hotkey_is_mouse = False
                self.hotkey = key
                self.hotkey_input.setText(self.get_key_name(key))
                self.hotkey_capture_active = False
                return
            
            # Capture zoom hotkey
            if self.zoom_hotkey_capture_active:
                self.zoom_hotkey_is_mouse = False
                self.zoom_hotkey = key
                self.zoom_hotkey_input.setText(self.get_key_name(key))
                self.zoom_hotkey_capture_active = False
                return
            
            # Toggle settings window
            if key == Key.insert:
                self.setVisible(not self.isVisible())
                return
            
            # Toggle magnifier (if not mouse hotkey)
            if not self.hotkey_is_mouse and key == self.hotkey:
                if self.toggle_mode:
                    self.toggle_magnifier_visibility()
                else:
                    self.show_magnifier()
            
            # Toggle zoom preset (if not mouse hotkey)
            if not self.zoom_hotkey_is_mouse and key == self.zoom_hotkey:
                self.magnifier.toggle_zoom_preset()
        
        def on_key_release(key):
            # Hold mode release
            if not self.hotkey_is_mouse and not self.toggle_mode and key == self.hotkey:
                self.hide_magnifier()
        
        def on_mouse_click(x, y, button, pressed):
            if pressed:
                # Capture hotkey
                if self.hotkey_capture_active:
                    self.hotkey_is_mouse = True
                    self.hotkey_mouse_button = button
                    self.hotkey_input.setText(self.get_button_name(button))
                    self.hotkey_capture_active = False
                    return
                
                # Capture zoom hotkey
                if self.zoom_hotkey_capture_active:
                    self.zoom_hotkey_is_mouse = True
                    self.zoom_hotkey_mouse_button = button
                    self.zoom_hotkey_input.setText(self.get_button_name(button))
                    self.zoom_hotkey_capture_active = False
                    return
                
                # Toggle magnifier (if mouse hotkey)
                if self.hotkey_is_mouse and button == self.hotkey_mouse_button:
                    if self.toggle_mode:
                        self.toggle_magnifier_visibility()
                    else:
                        self.show_magnifier()
                
                # Toggle zoom preset (if mouse hotkey)
                if self.zoom_hotkey_is_mouse and button == self.zoom_hotkey_mouse_button:
                    self.magnifier.toggle_zoom_preset()
            else:
                # Hold mode release
                if self.hotkey_is_mouse and not self.toggle_mode and button == self.hotkey_mouse_button:
                    self.hide_magnifier()
        
        # Setup listeners
        try:
            self.key_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
            self.key_listener.start()
            
            self.mouse_listener = mouse.Listener(on_click=on_mouse_click)
            self.mouse_listener.start()
            
            logger.info("Keyboard and mouse listeners started successfully")
        except Exception as e:
            error_message = f"Error setting up input listeners: {e}"
            logger.error(error_message)
            QMessageBox.critical(
                self,
                "Critical Error",
                error_message + "\nGlobal hotkeys will not work.",
                QMessageBox.Ok
            )
    
    def get_key_name(self, key):
        """
        Get displayable name for a key.
        
        Args:
            key: The key object from pynput
            
        Returns:
            str: Human-readable name of the key
        """
        try:
            if hasattr(key, 'char'):
                if key.char:
                    return key.char.upper()
                else:
                    return "Unknown"
            else:
                # Handle special keys
                key_name = str(key).replace('Key.', '')
                return key_name.capitalize()
        except:
            return "Unknown"
    
    def get_button_name(self, button):
        """
        Get displayable name for a mouse button.
        
        Args:
            button: The button object from pynput
            
        Returns:
            str: Human-readable name of the button
        """
        if button == Button.left:
            return "Left Button"
        elif button == Button.right:
            return "Right Button"
        elif button == Button.middle:
            return "Middle Button"
        else:
            return f"Mouse Button {button}"
    
    def toggle_magnifier_visibility(self):
        """Toggle the visibility of the magnifier."""
        self.window_visible = not self.window_visible
        
        if self.window_visible:
            self.show_magnifier()
        else:
            self.hide_magnifier()
    
    def show_magnifier(self):
        """Show the magnifier or offset overlay."""
        self.window_visible = True
        if self.offset_display_checkbox.isChecked() and self.offset_overlay:
            self.offset_overlay.show()
        else:
            self.magnifier.show_window()
    
    def hide_magnifier(self):
        """Hide the magnifier or offset overlay."""
        self.window_visible = False
        if self.offset_display_checkbox.isChecked() and self.offset_overlay:
            self.offset_overlay.hide()
        else:
            self.magnifier.hide_window()
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Don't actually close, just hide the window
        if event.spontaneous():
            event.ignore()
            self.hide()
        else:
            # This is a programmatic close, allow it
            event.accept()
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        # Hide window on Escape key
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
