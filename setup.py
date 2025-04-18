#!/usr/bin/env python3
"""
Setup script for PyScope - A Python-based screen magnifier for gamers.

This script handles the packaging and installation of PyScope, making it
available as both an importable Python package and a standalone application
that can be launched from the command line.
"""

import os
import sys
from setuptools import setup, find_packages

# Import version from package without installing it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'pyscope')))
try:
    from pyscope import __version__
except ImportError:
    __version__ = '0.1.0'  # Default if import fails

# Read the long description from README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Define required packages
requirements = [
    'PyQt5>=5.15.0',       # For GUI components
    'pynput>=1.7.0',       # For global hotkeys
    'mss>=6.1.0',          # For fast screen capture
    'Pillow>=8.0.0',       # For image processing
    'numpy>=1.20.0',       # For calculations and transformations
]

# Additional packages for specific platforms
if sys.platform.startswith('win'):
    requirements.append('pywin32>=300')  # Windows-specific functionality

setup(
    name='pyscope',
    version=__version__,
    author='PyScope Team',
    author_email='info@pyscope.org',
    description='A Python-based screen magnifier for gamers',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pyscope/pyscope',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Games/Entertainment',
        'Topic :: Utilities',
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
    ],
    python_requires='>=3.7',
    install_requires=requirements,
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
        'pyscope': ['resources/*'],
    },
    # Project info
    keywords='magnifier, screen, gaming, accessibility, zoom',
    project_urls={
        'Bug Reports': 'https://github.com/pyscope/pyscope/issues',
        'Source': 'https://github.com/pyscope/pyscope',
    },
)
