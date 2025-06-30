"""
PyGoPS - Python wrapper for Go applications with PowerShell launcher
"""

from .go_launcher import GoLauncher
from .go_server   import GoServer
from .go_thread   import GoThread

__version__     = "0.1.2"
__author__      = "genderlesspit"
__description__ = "Python wrapper for Go applications with PowerShell launcher"

__all__ = ["GoLauncher","GoServer","GoThread"]