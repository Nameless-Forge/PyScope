"""
Screen magnification core functionality for PyScope.

This module provides the main Magnifier class which handles capturing, zooming,
and displaying screen content. It uses platform-specific optimizations where
available (Windows Magnification API) and falls back to a screen capture approach
on other platforms.
"""

import numpy as np
import platform
import sys
import logging
import ctypes
from ctypes import windll, c_int, c_float, Structure, POINTER, WinError, WINFUNCTYPE, byref
from ctypes.wintypes import BOOL, HWND, RECT, DWORD, ULONG
from PIL import Image, ImageQt
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer, QSize, QRectF, QThread  # Added QRectF, QThread
from PyQt5.QtGui import QPainterPath, QPainter, QPen, QColor, QImage  # Added QImage
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QRegion
import mss


# Set up logger
logger = logging.getLogger(__name__)


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
        self.use_native_api = False
        self.native_magnifier = None

        # Screen capture (for non-native approach)
        self.sct = None

        # System info
        self.system = platform.system()
        logger.info(f"Initializing magnifier on {self.system}")

    def initialize(self):
        """
        Initialize the magnifier window and resources.

        This method prepares the magnifier by:
        1. Creating the application window
        2. Setting up platform-specific magnification capabilities
        3. Initializing the refresh timer

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if self.is_initialized:
            return True

        try:
            # Create window instance
            if QApplication.instance() is None:
                # Create application only if it doesn't exist
                self.app = QApplication(sys.argv)

            # Try to initialize native magnification API
            self._initialize_platform_specific()

            # Create the magnifier window
            self.window = MagnifierWindow(self)

            # Set up refresh timer
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_magnifier)
            self.set_refresh_rate(self.refresh_rate)

            self.is_initialized = True
            logger.info("Magnifier successfully initialized")
            return True

        except Exception as e:
            logger.error(f"Error initializing magnifier: {e}", exc_info=True)
            return False

    def _initialize_platform_specific(self):
        """
        Initialize platform-specific magnification capabilities.

        On Windows, attempts to use the Windows Magnification API.
        On other platforms, falls back to screen capture approach.
        """
        if self.system == "Windows":
            try:
                # Try to use Windows Magnification API
                self.native_magnifier = WindowsMagnifier()
                self.use_native_api = self.native_magnifier.initialize()
                if self.use_native_api:
                    logger.info("Using Windows Magnification API")
                    # Set initial properties
                    self.native_magnifier.set_window_size(self.width, self.height)
                    self.native_magnifier.set_zoom_level(self.zoom_level)
                    self.native_magnifier.set_window_shape(self.circular)
                    return
                logger.warning("Failed to initialize Windows Magnification API, falling back to screen capture")
            except Exception as e:
                logger.warning(f"Error initializing Windows Magnification API: {e}")
                self.use_native_api = False

        # Fallback to screen capture method
        logger.info("Using screen capture magnification method")
        self.sct = mss.mss()

    def set_resolution(self, width, height):
        """
        Set the size of the magnifier window.

        Args:
            width (int): Width of the magnifier window in pixels
            height (int): Height of the magnifier window in pixels
        """
        self.width = width
        self.height = height

        # Update window size
        if self.window:
            self.window.resize(width, height)
            self.window.update_shape()

        # Update native magnifier if using it
        if self.use_native_api and self.native_magnifier:
            self.native_magnifier.set_window_size(width, height)

    def set_window_shape(self, circular):
        """
        Set the shape of the magnifier window (circular or rectangular).

        Args:
            circular (bool): True for circular shape, False for rectangular
        """
        self.circular = circular

        # Update window shape
        if self.window:
            self.window.update_shape()

        # Update native magnifier if using it
        if self.use_native_api and self.native_magnifier:
            self.native_magnifier.set_window_shape(circular)

    def set_refresh_rate(self, refresh_rate):
        """
        Set the refresh rate (FPS) of the magnifier.

        Args:
            refresh_rate (int): Frames per second (1-144)
        """
        self.refresh_rate = max(1, min(144, refresh_rate))

        # Update timer interval
        if self.timer:
            interval = int(1000 / self.refresh_rate)
            self.timer.setInterval(interval)

        # Update native magnifier if using it
        if self.use_native_api and self.native_magnifier:
            self.native_magnifier.set_refresh_rate(refresh_rate)

    def set_zoom(self, zoom_level):
        """
        Set the zoom level for magnification.

        Args:
            zoom_level (float): Zoom level (1.0 or greater)
        """
        self.zoom_level = max(1.0, zoom_level)

        # Update native magnifier if using it
        if self.use_native_api and self.native_magnifier:
            self.native_magnifier.set_zoom_level(self.zoom_level)

    def toggle_zoom_preset(self):
        """
        Toggle between high and low zoom presets.

        This switches between the two configured zoom levels (zoom_level_low and
        zoom_level_high) each time it's called, making it easy to quickly change
        magnification power with a single hotkey.

        Returns:
            bool: The current zoom state (True for low zoom, False for high zoom)
        """
        self.zoom_state = not self.zoom_state
        if self.zoom_state:
            self.set_zoom(self.zoom_level_low)
        else:
            self.set_zoom(self.zoom_level_high)
        return self.zoom_state

    def move_window(self, x_offset, y_offset):
        """
        Set the offset position of the magnifier from screen center.

        Args:
            x_offset (int): Horizontal offset from center in pixels
            y_offset (int): Vertical offset from center in pixels
        """
        self.x_offset = x_offset
        self.y_offset = y_offset

        # Update window position
        if self.window:
            self._update_window_position()

        # Update native magnifier if using it
        if self.use_native_api and self.native_magnifier:
            self.native_magnifier.move_window(x_offset, y_offset)

    def _update_window_position(self):
        """Update the window position based on current settings."""
        if not self.window:
            return

        screen_width = QApplication.desktop().screenGeometry().width()
        screen_height = QApplication.desktop().screenGeometry().height()
        x = (screen_width - self.width) // 2 + self.x_offset
        y = (screen_height - self.height) // 2 + self.y_offset
        self.window.move(x, y)

    def safe_start_timer(self):
        """Start the timer from the main GUI thread."""
        if self.timer:
            if QApplication.instance().thread() == QThread.currentThread():
                # Already in the main thread
                self.timer.start()
            else:
                # Create a single-shot timer to start our main timer in the main thread
                QTimer.singleShot(0, self.timer.start)

    def safe_stop_timer(self):
        """Stop the timer from the main GUI thread."""
        if self.timer:
            if QApplication.instance().thread() == QThread.currentThread():
                # Already in the main thread
                self.timer.stop()
            else:
                # Create a single-shot timer to stop our main timer in the main thread
                QTimer.singleShot(0, self.timer.stop)

    def show_window(self):
        """Show the magnifier window."""
        if not self.is_initialized:
            self.initialize()

        if self.use_native_api and self.native_magnifier:
            # Use native magnifier
            self.native_magnifier.show_window()
            self.visible = True
            return

        # Use Qt window
        if self.window:
            self._update_window_position()
            QTimer.singleShot(0, lambda: self.window.show())  # Show window in main thread
            self.safe_start_timer()  # Start timer safely
            self.visible = True

    def hide_window(self):
        """Hide the magnifier window."""
        if self.use_native_api and self.native_magnifier:
            # Use native magnifier
            self.native_magnifier.hide_window()
            self.visible = False
            return

        # Use Qt window
        if self.window:
            QTimer.singleShot(0, lambda: self.window.hide())  # Hide window in main thread
            self.safe_stop_timer()  # Stop timer safely
            self.visible = False

    def toggle_visibility(self):
        """
        Toggle the visibility of the magnifier window.

        Returns:
            bool: True if now visible, False if now hidden
        """
        if self.visible:
            self.hide_window()
        else:
            self.show_window()
        return self.visible

    def is_visible(self):
        """
        Check if the magnifier window is currently visible.

        Returns:
            bool: True if visible, False if hidden
        """
        return self.visible

    def update_magnifier(self):
        """Update the magnified content."""
        if not self.visible or not self.window:
            return

        # Skip update if using native magnifier - it handles its own updates
        if self.use_native_api and self.native_magnifier:
            return

        try:
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

            # Check if monitor definition needs to be updated (optimize by not recreating every frame)
            monitor = {"top": top, "left": left, "width": scaled_width, "height": scaled_height}

            # Capture the screen region
            screenshot = self.sct.grab(monitor)

            # Convert to PIL Image and resize
            # Use LANCZOS for better quality when scaling up
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img = img.resize((self.width, self.height), Image.LANCZOS)

            # Update the window with the new image
            self.window.set_image(img)
        except Exception as e:
            logger.error(f"Error updating magnifier content: {e}")

    def dispose(self):
        """Clean up resources and prepare for application exit."""
        logger.info("Disposing magnifier resources")

        if self.timer:
            self.timer.stop()

        if self.window:
            self.window.close()

        if self.sct:
            self.sct.close()

        if self.use_native_api and self.native_magnifier:
            self.native_magnifier.dispose()

        self.is_initialized = False


class MagnifierWindow(QWidget):
    """Window class for displaying the magnified content."""

    def __init__(self, magnifier):
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

        if platform.system() == "Windows":
            try:
                WDA_EXCLUDEFROMCAPTURE = 0x11
                windll.user32.SetWindowDisplayAffinity(
                    int(self.winId()), WDA_EXCLUDEFROMCAPTURE
                )
            except Exception as e:
                logger.warning(f"SetWindowDisplayAffinity failed: {e}")

        # Set initial size
        self.resize(magnifier.width, magnifier.height)

        # Update window shape (circular/rectangular)
        self.update_shape()

    def set_image(self, image):
        """
        Set the image to display.

        Args:
            image (PIL.Image): The image to display
        """
        # Convert PIL image to QImage properly
        img_data = image.convert("RGBA").tobytes("raw", "RGBA")
        self.image = QImage(img_data, image.width, image.height, QImage.Format_RGBA8888)
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
        """
        Handle painting of the magnified content.

        Args:
            event (QPaintEvent): The paint event
        """
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

        # Use QRectF instead of QRect for better compatibility
        target_rect = QRectF(0, 0, self.width(), self.height())
        painter.drawImage(target_rect, self.image)


class WindowsMagnifier:
    """Windows-specific magnification implementation using the Windows Magnification API."""

    # Constants from WinUser.h and Magnification.h
    MS_SHOWMAGNIFIEDCURSOR = 0x0001
    MS_CLIPAROUNDCURSOR = 0x0002
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOPMOST = 0x00000008
    WS_POPUP = 0x80000000
    WS_VISIBLE = 0x10000000
    WC_MAGNIFIER = "Magnifier" # Class name for magnifier control

    def __init__(self):
        """Initialize the Windows Magnification API wrapper."""
        self.hwnd_magnifier = None
        self.hwnd_host = None
        self.width = 400
        self.height = 400
        self.circular = True
        self.refresh_rate = 60
        self.zoom_level = 2.0
        self.x_offset = 0
        self.y_offset = 0
        self.timer_id = 1
        self.initialized = False

        # Windows-specific resources
        self.timer_func = None
        self.wnd_proc = None
        self.user32 = None
        self.magnification = None
        self.gdi32 = None

        # MAGTRANSFORM matrix structure - 3x3 matrix of floats
        class MAGTRANSFORM(Structure):
            _fields_ = [("v", c_float * 9)]
        self.MAGTRANSFORM = MAGTRANSFORM

        # RECT structure
        class RECT(Structure):
            _fields_ = [
                ("left", c_int),
                ("top", c_int),
                ("right", c_int),
                ("bottom", c_int)
            ]
        self.RECT = RECT

    def initialize(self):
        """
        Initialize the Windows Magnification API.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Check if we're on Windows
            if platform.system() != "Windows":
                logger.warning("Windows Magnification API is only available on Windows")
                return False

            # Import required functions
            self.user32 = windll.user32
            self.magnification = windll.magnification
            self.gdi32 = windll.gdi32

            # Initialize magnification
            if not self.magnification.MagInitialize():
                logger.error(f"Failed to initialize Windows Magnification API. Error code: {WinError()}")
                return False

            # Define WndProc callback
            WndProc = WINFUNCTYPE(c_int, HWND, c_int, c_int, c_int)

            # Create the window proc callback
            def wnd_proc_callback(hwnd, msg, wparam, lparam):
                # WM_TIMER = 0x0113
                if msg == 0x0113 and wparam == self.timer_id:
                    self._update_content()
                    return 0
                # WM_DESTROY = 0x0002
                elif msg == 0x0002:
                    self.user32.PostQuitMessage(0)
                    return 0
                return self.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            # Store reference to prevent garbage collection
            self.wnd_proc = WndProc(wnd_proc_callback)

            # Register window class (simplified, normally needs WNDCLASSEXW structure)
            h_instance = windll.kernel32.GetModuleHandleW(None)
            class_name = "PyScope_Magnifier_Host"

            # Get screen dimensions for initial positioning
            screen_width = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_height = self.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        
            # Calculate initial position - ВАЖНО: используем расчет положения центра
            x = (screen_width - self.width) // 2 + self.x_offset
            y = (screen_height - self.height) // 2 + self.y_offset
        
            logger.info(f"Initial window position: x={x}, y={y}, width={self.width}, height={self.height}")

            # Create a basic host window using a standard class like "Static" first
            self.hwnd_host = self.user32.CreateWindowExW(
                WindowsMagnifier.WS_EX_TOPMOST | WindowsMagnifier.WS_EX_LAYERED | WindowsMagnifier.WS_EX_TRANSPARENT,
                "Static", # Using a predefined class
                "PyScope Magnifier",
                WindowsMagnifier.WS_POPUP,
                x, y, self.width, self.height,  # Явное указание начальной позиции!
                None, None, None, None
            )

            if not self.hwnd_host:
                logger.error(f"Failed to create host window. Error code: {WinError()}")
                self.magnification.MagUninitialize()
                return False

            # Create magnifier control window as a child of the host
            magnifier_style = self.WS_VISIBLE | 0x40000000 | self.MS_SHOWMAGNIFIEDCURSOR

            self.hwnd_magnifier = self.user32.CreateWindowExW(
                0,                               # dwExStyle
                self.WC_MAGNIFIER,               # lpClassName
                "PyScope Magnifier Control",     # lpWindowName
                magnifier_style,                 # dwStyle
                0, 0, self.width, self.height,   # x, y, w, h внутри родителя
                self.hwnd_host,                  # hWndParent
                None, h_instance, None           # hMenu, hInstance, lpParam
            )

            if not self.hwnd_magnifier:
                logger.error(f"Failed to create magnifier window. Error code: {WinError()}")
                self.user32.DestroyWindow(self.hwnd_host)
                self.magnification.MagUninitialize()
                return False

            # Проверка и логирование получившейся геометрии окна
            rc = self.RECT()
            if self.user32.GetWindowRect(self.hwnd_host, byref(rc)):
                logger.info(f"Host window rect: left={rc.left}, top={rc.top}, right={rc.right}, bottom={rc.bottom}")
            
                # Проверка, соответствует ли позиция ожидаемой
                if rc.left != x or rc.top != y:
                    logger.warning(f"Window position mismatch: expected ({x},{y}), got ({rc.left},{rc.top})")
                
                    # Попытка принудительно установить позицию
                    if not self.user32.SetWindowPos(
                        self.hwnd_host, -1, x, y, self.width, self.height, 0
                    ):
                        logger.warning(f"Failed to correct window position: {WinError()}")
            else:
                logger.warning("Failed to get window rectangle.")

            # Set initial transform
            transform = self.MAGTRANSFORM()
            transform.v[0] = float(self.zoom_level)  # x scale
            transform.v[4] = float(self.zoom_level)  # y scale
            transform.v[8] = 1.0  # Additional scale factor

            if not self.magnification.MagSetWindowTransform(self.hwnd_magnifier, byref(transform)):
                logger.error(f"Failed to set magnification transform. Error code: {WinError()}")
                self.user32.DestroyWindow(self.hwnd_magnifier)
                self.user32.DestroyWindow(self.hwnd_host)
                self.magnification.MagUninitialize()
                return False

            # Убедимся, что окно точно на правильной позиции
            self._update_window_position()
        
            # Set window shape if circular after setting size/position
            if self.circular:
                self._set_circular_region()

            # Set refresh timer on the host window
            interval = int(1000 / self.refresh_rate)
            if not self.user32.SetTimer(self.hwnd_host, self.timer_id, interval, self.wnd_proc):
                logger.error(f"Failed to set timer. Error code: {WinError()}")

            # Для полной уверенности запускаем обновление содержимого сразу
            self._update_content()

            self.initialized = True
            logger.info("Windows Magnifier initialized.")
            return True

        except Exception as e:
            logger.error(f"Error initializing Windows Magnification API: {e}", exc_info=True)
            self._cleanup_resources()
            return False

    def _set_circular_region(self):
        """Set a circular region for the window."""
        if not self.hwnd_host or not self.gdi32:
             return

        try:
            # Create circular region
            # Note: CreateEllipticRgn is in gdi32
            region = self.gdi32.CreateEllipticRgn(0, 0, self.width, self.height)
            if region:
                # SetWindowRgn takes ownership of the region object if third param is True
                self.user32.SetWindowRgn(self.hwnd_host, region, True)
                # Do not call DeleteObject if SetWindowRgn succeeds with True
            else:
                logger.warning(f"Failed to create elliptic region. Error code: {WinError()}")
        except Exception as e:
            logger.error(f"Error setting circular region: {e}")


    def _update_window_position(self):
        """Update the window position based on current settings."""
        if not self.hwnd_host or not self.user32:
            return

        try:
            # Get screen dimensions
            screen_width = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_height = self.user32.GetSystemMetrics(1)  # SM_CYSCREEN

            # Calculate window position
            x = (screen_width - self.width) // 2 + self.x_offset
            y = (screen_height - self.height) // 2 + self.y_offset

            logger.info(f"Setting window position: x={x}, y={y}, width={self.width}, height={self.height}")

            flags = 0x0010  # SWP_NOACTIVATE
            # Move host window
            self.user32.SetWindowPos(
                self.hwnd_host,
                -1,  # HWND_TOPMOST
                x, y, self.width, self.height,
                flags
            )
            # Resize magnifier control
            self.user32.SetWindowPos(
                self.hwnd_magnifier,
                None,
                0, 0,
                self.width, self.height,
                flags
            )
            # Force repaint
            self.user32.UpdateWindow(self.hwnd_host)

        except Exception as e:
            logger.error(f"Error updating window position: {e}")

    def _update_content(self):
        """Update the magnified content."""
        if not self.hwnd_magnifier or not self.magnification or not self.user32:
            return

        try:
            # Get screen dimensions
            screen_width = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            screen_height = self.user32.GetSystemMetrics(1)  # SM_CYSCREEN

            # Calculate center point
            center_x = (screen_width // 2) + self.x_offset
            center_y = (screen_height // 2) + self.y_offset

            # Calculate source rectangle size
            # Ensure zoom level is not zero to avoid division by zero
            safe_zoom = max(1.0, self.zoom_level)
            scaled_width = int(self.width / safe_zoom)
            scaled_height = int(self.height / safe_zoom)

            # Calculate source rectangle bounds
            left = center_x - scaled_width // 2
            top = center_y - scaled_height // 2
            right = left + scaled_width
            bottom = top + scaled_height

            # Ensure bounds are within screen limits (optional, MagSetWindowSource might handle this)
            left = max(0, min(left, screen_width - scaled_width))
            top = max(0, min(top, screen_height - scaled_height))
            right = left + scaled_width
            bottom = top + scaled_height


            source_rect = self.RECT(left, top, right, bottom)

            # Set the source rectangle
            if not self.magnification.MagSetWindowSource(self.hwnd_magnifier, source_rect):
                 # Log error non-intrusively, maybe the window is hidden
                 # logger.warning(f"Failed to set window source. Error: {WinError()}")
                 pass # Avoid spamming logs if window is hidden

            # Force repaint (Needed?) Mag API might handle this.
            # self.user32.InvalidateRect(self.hwnd_host, None, True) # Invalidate host
            # self.user32.UpdateWindow(self.hwnd_host)

        except Exception as e:
            logger.error(f"Error updating Windows magnifier content: {e}")

    def set_window_size(self, width, height):
        """
        Set the size of the magnifier window.

        Args:
            width (int): Width of the magnifier window in pixels
            height (int): Height of the magnifier window in pixels
        """
        self.width = width
        self.height = height

        if self.hwnd_host and self.initialized:
            # Update window position and size
            self._update_window_position()

            # Update window shape if circular
            if self.circular:
                self._set_circular_region()
            else:
                # Ensure rectangular shape if not circular
                 self.user32.SetWindowRgn(self.hwnd_host, None, True)


    def set_window_shape(self, circular):
        """
        Set the shape of the magnifier window.

        Args:
            circular (bool): True for circular shape, False for rectangular
        """
        self.circular = circular

        if self.hwnd_host and self.initialized:
            if circular:
                self._set_circular_region()
            else:
                # Reset to rectangular shape by removing the region
                self.user32.SetWindowRgn(self.hwnd_host, None, True)

    def set_refresh_rate(self, refresh_rate):
        """
        Set the refresh rate of the magnifier.

        Args:
            refresh_rate (int): Frames per second (1-144)
        """
        self.refresh_rate = max(1, min(144, refresh_rate))

        if self.hwnd_host and self.initialized:
            # Update timer
            self.user32.KillTimer(self.hwnd_host, self.timer_id)
            interval = int(1000 / self.refresh_rate)
            if not self.user32.SetTimer(self.hwnd_host, self.timer_id, interval, self.wnd_proc):
                logger.error(f"Failed to reset timer. Error code: {WinError()}")


    def set_zoom_level(self, zoom_level):
        """
        Set the zoom level for magnification.

        Args:
            zoom_level (float): Zoom level (1.0 or greater)
        """
        self.zoom_level = max(1.0, zoom_level)

        if self.hwnd_magnifier and self.initialized:
            # Create identity matrix
            transform = self.MAGTRANSFORM()
            # Identity matrix setup
            transform.v[0] = 0.0; transform.v[1] = 0.0; transform.v[2] = 0.0
            transform.v[3] = 0.0; transform.v[4] = 0.0; transform.v[5] = 0.0
            transform.v[6] = 0.0; transform.v[7] = 0.0; transform.v[8] = 0.0
            # Apply zoom
            transform.v[0] = float(self.zoom_level)  # x scale
            transform.v[4] = float(self.zoom_level)  # y scale
            transform.v[8] = 1.0                     # w scale

            # Set the transform
            if not self.magnification.MagSetWindowTransform(self.hwnd_magnifier, byref(transform)):
                logger.warning(f"Failed to set window transform on zoom. Error: {WinError()}")


    def move_window(self, x_offset, y_offset):
        """
        Set the offset position of the magnifier from screen center.

        Args:
            x_offset (int): Horizontal offset from center in pixels
            y_offset (int): Vertical offset from center in pixels
        """
        self.x_offset = x_offset
        self.y_offset = y_offset

        if self.hwnd_host and self.initialized:
            self._update_window_position()

    def show_window(self):
        """Show the magnifier window."""
        logger.info("Attempting to show Windows Magnifier window")
    
        if not self.hwnd_host or not self.user32 or not self.initialized:
            logger.warning("Cannot show window - missing handles or not initialized")
            return
    
        # Update position before showing
        self._update_window_position()
    
        # Make a small pause to ensure position is applied
        import time
        time.sleep(0.05)
    
        # Show window with flag SW_SHOWNA (8) - show without activation
        result = self.user32.ShowWindow(self.hwnd_host, 8)
        logger.info(f"ShowWindow show result: {result}")
    
        # CRITICAL: Recreate the timer for updates
        interval = int(1000 / self.refresh_rate)
        timer_result = self.user32.SetTimer(self.hwnd_host, self.timer_id, interval, self.wnd_proc)
        logger.info(f"Timer recreation result: {timer_result}")
    
        if not timer_result:
            logger.error(f"Failed to recreate timer: {WinError()}")
    
        # Reset the transform to ensure it's properly applied
        transform = self.MAGTRANSFORM()
        transform.v[0] = float(self.zoom_level)  # x scale
        transform.v[4] = float(self.zoom_level)  # y scale
        transform.v[8] = 1.0  # Additional scale factor
    
        self.magnification.MagSetWindowTransform(self.hwnd_magnifier, byref(transform))
    
        # Update content immediately
        self._update_content()
    
        # Update position again after showing
        self._update_window_position()
    
        logger.info("Windows Magnifier window shown and updates enabled")

    def hide_window(self):
        """Hide the magnifier window."""
        logger.info("Attempting to hide Windows Magnifier window")
    
        if not self.hwnd_host or not self.user32 or not self.initialized:
            logger.warning("Cannot hide window - missing handles or not initialized")
            return
        
        # First kill the timer to stop updates
        try:
            result = self.user32.KillTimer(self.hwnd_host, self.timer_id)
            logger.info(f"Killed timer: {result}")
        except Exception as e:
            logger.error(f"Error killing timer: {e}")
    
        # Try to hide the window
        try:
            # SW_HIDE = 0
            result = self.user32.ShowWindow(self.hwnd_host, 0)
            logger.info(f"ShowWindow hide result: {result}")
        
            # Additional force-hide attempt
            if not result:
                # Try with different flags
                result = self.user32.SetWindowPos(
                    self.hwnd_host,
                    0,  # HWND_TOP
                    0, 0, 0, 0,
                    0x0080 | 0x0400  # SWP_HIDEWINDOW | SWP_NOMOVE
                )
                logger.info(f"SetWindowPos hide result: {result}")
            
            # Check if window is actually hidden
            style = self.user32.GetWindowLongW(self.hwnd_host, -16)  # GWL_STYLE
            is_visible = (style & 0x10000000) != 0  # WS_VISIBLE
            logger.info(f"Window visible state after hide: {is_visible}")
        
            if is_visible:
                logger.warning("Window is still visible after hide attempt")
        except Exception as e:
            logger.error(f"Error hiding window: {e}")
        
        logger.info("Windows Magnifier hide_window completed")

    def dispose(self):
        """Clean up resources."""
        logger.info("Disposing Windows Magnifier resources")
        self._cleanup_resources()

    def _cleanup_resources(self):
        """Clean up all Windows resources."""
        try:
            # Kill timer
            if self.hwnd_host and self.user32:
                self.user32.KillTimer(self.hwnd_host, self.timer_id)

            # Destroy windows (Child first)
            if self.hwnd_magnifier and self.user32:
                self.user32.DestroyWindow(self.hwnd_magnifier)
                self.hwnd_magnifier = None

            if self.hwnd_host and self.user32:
                self.user32.DestroyWindow(self.hwnd_host)
                self.hwnd_host = None

            # Uninitialize magnification API
            if self.initialized and self.magnification:
                self.magnification.MagUninitialize()

            self.initialized = False
            self.wnd_proc = None # Release reference

        except Exception as e:
            logger.error(f"Error cleaning up Windows Magnification resources: {e}")
