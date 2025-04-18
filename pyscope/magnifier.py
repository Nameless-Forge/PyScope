import numpy as np
from PIL import Image, ImageQt
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer, QPainterPath
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QRegion
from PyQt5.QtWidgets import QWidget, QApplication
import mss
import platform
import sys


class Magnifier:
    """Main class for screen magnification functionality."""
    
    def __init__(self):
        """Initialize the magnifier with default settings."""
        # Main settings
        self.width = 400
        self.height = 400
        self.circular = True
        self.refresh_rate = 60
        self.x_offset = 0
        self.y_offset = 0
        self.zoom_level = 2.0
        self.zoom_level_high = 4.0
        self.zoom_level_low = 2.0
        self.zoom_state = False
        
        # Internal state
        self.visible = False
        self.is_initialized = False
        self.window = None
        self.timer = None
        self.app = None
        
        # Screen capture
        self.sct = mss.mss()
    
    def initialize(self):
        """Initialize the magnifier window and resources."""
        if self.is_initialized:
            return True
            
        # Create window instance
        if QApplication.instance() is None:
            # Create application only if it doesn't exist
            self.app = QApplication(sys.argv)
        
        self.window = MagnifierWindow(self)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_magnifier)
        self.set_refresh_rate(self.refresh_rate)
        
        self.is_initialized = True
        return True
    
    def set_resolution(self, width, height):
        """Set the size of the magnifier window."""
        self.width = width
        self.height = height
        if self.window:
            self.window.resize(width, height)
            self.window.update_shape()
    
    def set_window_shape(self, circular):
        """Set the shape of the magnifier window (circular or rectangular)."""
        self.circular = circular
        if self.window:
            self.window.update_shape()
    
    def set_refresh_rate(self, refresh_rate):
        """Set the refresh rate (FPS) of the magnifier."""
        self.refresh_rate = max(1, min(144, refresh_rate))
        if self.timer:
            interval = int(1000 / self.refresh_rate)
            self.timer.setInterval(interval)
    
    def set_zoom(self, zoom_level):
        """Set the zoom level for magnification."""
        self.zoom_level = max(1.0, zoom_level)
    
    def toggle_zoom_preset(self):
        """Toggle between high and low zoom presets."""
        self.zoom_state = not self.zoom_state
        if self.zoom_state:
            self.set_zoom(self.zoom_level_low)
        else:
            self.set_zoom(self.zoom_level_high)
        return self.zoom_state
    
    def move_window(self, x_offset, y_offset):
        """Set the offset position of the magnifier from screen center."""
        self.x_offset = x_offset
        self.y_offset = y_offset
        if self.window:
            self._update_window_position()
    
    def _update_window_position(self):
        """Update the window position based on current settings."""
        if not self.window:
            return
            
        screen_width = QApplication.desktop().screenGeometry().width()
        screen_height = QApplication.desktop().screenGeometry().height()
        x = (screen_width - self.width) // 2 + self.x_offset
        y = (screen_height - self.height) // 2 + self.y_offset
        self.window.move(x, y)
    
    def show_window(self):
        """Show the magnifier window."""
        if not self.is_initialized:
            self.initialize()
        
        if self.window:
            self._update_window_position()
            self.window.show()
            self.timer.start()
            self.visible = True
    
    def hide_window(self):
        """Hide the magnifier window."""
        if self.window:
            self.window.hide()
            self.timer.stop()
            self.visible = False
    
    def toggle_visibility(self):
        """Toggle the visibility of the magnifier window."""
        if self.visible:
            self.hide_window()
        else:
            self.show_window()
        return self.visible
    
    def is_visible(self):
        """Check if the magnifier window is currently visible."""
        return self.visible
    
    def update_magnifier(self):
        """Update the magnified content."""
        if not self.visible or not self.window:
            return
        
        # Get screen size
        screen_width = QApplication.desktop().screenGeometry().width()
        screen_height = QApplication.desktop().screenGeometry().height()
        
        # Calculate the center of the screen with offset
        center_x = screen_width // 2 + self.x_offset
        center_y = screen_height // 2 + self.y_offset
        
        # Calculate the source rectangle to capture
        scaled_width = int(self.width / self.zoom_level)
        scaled_height = int(self.height / self.zoom_level)
        
        # Calculate capture area
        left = center_x - scaled_width // 2
        top = center_y - scaled_height // 2
        
        # Ensure the capture area is within the screen bounds
        left = max(0, min(left, screen_width - scaled_width))
        top = max(0, min(top, screen_height - scaled_height))
        
        # Capture the screen region
        monitor = {"top": top, "left": left, "width": scaled_width, "height": scaled_height}
        screenshot = self.sct.grab(monitor)
        
        # Convert to PIL Image and resize
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img = img.resize((self.width, self.height), Image.LANCZOS)
        
        # Update the window with the new image
        self.window.set_image(img)
    
    def dispose(self):
        """Clean up resources."""
        if self.timer:
            self.timer.stop()
        if self.window:
            self.window.close()
        self.sct.close()
        self.is_initialized = False


class MagnifierWindow(QWidget):
    """Window class for displaying the magnified content."""
    
    def __init__(self, magnifier):
        """Initialize the magnifier window."""
        super().__init__()
        self.magnifier = magnifier
        self.image = None
        
        # Set window properties
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # Set initial size
        self.resize(magnifier.width, magnifier.height)
        
        # Update window shape (circular/rectangular)
        self.update_shape()
    
    def set_image(self, image):
        """Set the image to display."""
        self.image = ImageQt.ImageQt(image)
        self.update()
    
    def update_shape(self):
        """Update the window shape based on settings."""
        if self.magnifier.circular:
            # Create a circular mask for the window
            region = QRegion(
                0, 0, 
                self.magnifier.width, 
                self.magnifier.height, 
                QRegion.Ellipse
            )
            self.setMask(region)
        else:
            # Restore rectangular shape
            self.clearMask()
    
    def paintEvent(self, event):
        """Handle painting of the magnified content."""
        if not self.image:
            return
            
        painter = QPainter(self)
        
        # Set up rendering for high quality
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Draw the magnified image
        if self.magnifier.circular:
            # Create a clipping path for the circular shape
            path = QPainterPath()
            path.addEllipse(0, 0, self.width(), self.height())
            painter.setClipPath(path)
        
        painter.drawImage(QRect(0, 0, self.width(), self.height()), self.image)
