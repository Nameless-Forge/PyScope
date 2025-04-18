#!/usr/bin/env python3
"""
Setup script for PyScope - A Python-based screen magnifier for gamers.

This script handles the packaging and installation of PyScope, making it
available as both an importable Python package and a standalone application
that can be launched from the command line.
"""

import os
import sys
import platform
import subprocess
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install

# Import version from package without installing it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'pyscope')))
try:
    from pyscope import __version__, __author__
except ImportError:
    __version__ = '0.1.0'  # Default if import fails
    __author__ = 'PyScope Team'

# Read the long description from README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Define base requirements (common to all platforms)
base_requirements = [
    'PyQt5>=5.15.0',       # For GUI components
    'pynput>=1.7.0',       # For global hotkeys
    'mss>=6.1.0',          # For fast screen capture
    'Pillow>=8.0.0',       # For image processing
    'numpy>=1.20.0',       # For calculations and transformations
]

# Define development requirements (for contributors)
dev_requirements = [
    'pytest>=6.0.0',       # For running tests
    'black>=21.5b2',       # For code formatting
    'flake8>=3.9.2',       # For code linting
    'sphinx>=4.0.2',       # For documentation
    'pyinstaller>=4.3',    # For creating standalone executables
]

# Platform-specific requirements
platform_requirements = {
    'win32': ['pywin32>=300'],     # Windows-specific functionality
    'darwin': [],                  # macOS-specific requirements (none yet)
    'linux': ['python-xlib>=0.29'] # For X11 integration on Linux
}

# Determine the current platform and add relevant dependencies
current_platform = sys.platform
if current_platform in platform_requirements:
    base_requirements.extend(platform_requirements[current_platform])

# Define Windows Magnification extension (only on Windows)
ext_modules = []
if sys.platform.startswith('win'):
    # This is just a placeholder for potential future native extensions
    # If we wanted to compile a C/C++ extension for Windows Magnification API:
    # ext_modules.append(
    #     Extension(
    #         'pyscope.native.win_magnifier',
    #         sources=['pyscope/native/win_magnifier.c'],
    #         libraries=['magnification', 'user32', 'gdi32'],
    #         include_dirs=[],
    #         library_dirs=[],
    #     )
    # )
    pass

# Custom commands
class CreateResourcesCommand(install):
    """Custom command to create resource directories."""
    
    def run(self):
        # Create resources directory
        resources_dir = os.path.join('pyscope', 'resources')
        if not os.path.exists(resources_dir):
            os.makedirs(resources_dir, exist_ok=True)
            print(f"Created resources directory: {resources_dir}")
        
        # Run the standard install
        install.run(self)

# Setup configuration
setup(
    name='pyscope',
    version=__version__,
    author=__author__,
    author_email='info@pyscope.org',
    description='A Python-based screen magnifier for gamers',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pyscope/pyscope',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Gamers',
        'Topic :: Games/Entertainment',
        'Topic :: Utilities',
        'Topic :: Desktop Environment :: Screen Magnifiers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Environment :: X11 Applications :: Qt',
        'Natural Language :: English',
    ],
    python_requires='>=3.7',
    install_requires=base_requirements,
    extras_require={
        'dev': dev_requirements,
        'windows': platform_requirements['win32'],
        'linux': platform_requirements['linux'],
        'macos': platform_requirements['darwin'],
        'all': dev_requirements + 
               platform_requirements['win32'] + 
               platform_requirements['linux'] + 
               platform_requirements['darwin']
    },
    entry_points={
        'console_scripts': [
            'pyscope=pyscope.main:main',
        ],
        'gui_scripts': [
            'pyscope-gui=pyscope.main:main',
        ],
    },
    # Include non-Python files
    include_package_data=True,
    package_data={
        'pyscope': [
            'resources/*',          # All resource files
            'resources/icons/*',    # Icons
            'resources/images/*',   # Images
        ],
    },
    data_files=[
        ('share/applications', ['pyscope.desktop']),  # Linux desktop entry
        ('share/pixmaps', ['pyscope/resources/icons/pyscope.png']), # Linux icon
    ],
    # Project info
    keywords='magnifier, screen, gaming, accessibility, zoom, targeting, overlay',
    project_urls={
        'Bug Reports': 'https://github.com/pyscope/pyscope/issues',
        'Source': 'https://github.com/pyscope/pyscope',
        'Documentation': 'https://pyscope.readthedocs.io/',
    },
    # Extensions
    ext_modules=ext_modules,
    # Custom commands
    cmdclass={
        'create_resources': CreateResourcesCommand,
    },
    # Zip_safe flag for egg installations
    zip_safe=False,
)
