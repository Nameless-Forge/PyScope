"""
PyScope - A Python-based screen magnifier for gamers.

PyScope provides a customizable magnifying overlay for games and applications,
allowing precise targeting and detail viewing without compromising gameplay.
"""

# Version information
__version__ = "0.1.0"
__author__ = "Kill_Me_I_Noobs"

# Import main classes for easier access
from .magnifier import Magnifier
from .magnifier_gui import MagnifierGUI

# Ensure utils package is properly imported
from . import utils
