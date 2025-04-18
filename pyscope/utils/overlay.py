"""
Offset overlay module for PyScope.

This module provides the OffsetOverlay class which displays a transparent overlay
to help visualize the position and size of the magnifier window.
"""

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import QWidget, QApplication


class OffsetOverlay(QWidget):
    """
    Transparent overlay window that shows the position and shape of the magnifier.
    
    This overlay is used to visualize where the magnification window will appear
    without actually showing the magnified content. It's useful for positioning
    the magnifier correctly before activating it.
    """
    
    def __init__(self, width, height, x_offset, y_offset, circular):
        """
        Initialize the overlay window.
        
        Args:
            width (int): Width of the magnifier window
            height (int): Height of the magnifier window
            x_offset (int): Horizontal offset from screen center
            y_offset (int): Vertical offset from screen center
            circular (bool): Whether the shape is circular or rectangular
        """
        super().__init__()
        
        # Store settings
        self.shape_width = width
        self.shape_height = height
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.circular = circular
        
        # Set window properties
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # Let mouse events pass through
        
        # Set to full screen size
        screen_rect = QApplication.desktop().screenGeometry()
        self.setGeometry(screen_rect)
    
    def update_settings(self, width, height, x_offset, y_offset, circular):
        """
        Update the overlay settings and redraw.
        
        Args:
            width (int): New width of the magnifier window
            height (int): New height of the magnifier window
            x_offset (int): New horizontal offset from screen center
            y_offset (int): New vertical offset from screen center
            circular (bool): New shape setting (circular or rectangular)
        """
        self.shape_width = width
        self.shape_height = height
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.circular = circular
        self.repaint()
    
    def paintEvent(self, event):
        """
        Paint the overlay with the shape outline and crosshair.
        
        This method draws the visual representation of where the magnifier
        will appear, including a crosshair in the center for precise alignment.
        """
        painter = QPainter(self)
        
        # Set up the painter
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Use red pen for visibility
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Calculate the center of the screen with offset
        screen_rect = QApplication.desktop().screenGeometry()
        center_x = screen_rect.width() // 2 + self.x_offset
        center_y = screen_rect.height() // 2 + self.y_offset
        
        # Calculate top-left corner of shape
        x = center_x - self.shape_width // 2
        y = center_y - self.shape_height // 2
        
        # Draw the shape (circular or rectangular)
        if self.circular:
            painter.drawEllipse(x, y, self.shape_width, self.shape_height)
        else:
            painter.drawRect(x, y, self.shape_width, self.shape_height)
        
        # Draw crosshair at center
        crosshair_size = 10
        painter.drawLine(center_x - crosshair_size, center_y, 
                         center_x + crosshair_size, center_y)
        painter.drawLine(center_x, center_y - crosshair_size, 
                         center_x, center_y + crosshair_size)
