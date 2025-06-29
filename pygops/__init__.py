"""
PyGoPS - Python wrapper for Go applications with PowerShell launcher
"""

import sys
from pathlib import Path
from typing import Optional

"""
PyGoPS - Python wrapper for Go applications with PowerShell launcher
"""

import sys
from pathlib import Path
from typing import Optional

def get_script_path(script_name: str = "go_launcher.ps1") -> Path:
    """Get path to bundled PowerShell script using modern importlib approach"""

    # Try modern importlib.resources first (Python 3.9+)
    if sys.version_info >= (3, 9):
        try:
            import importlib.resources as resources
            # For files outside the package, we need to reference the project root
            # Since scripts/ is at the same level as pygops/, we go up one level
            with resources.as_file(
                resources.files(__package__).parent / "scripts" / script_name
            ) as script_path:
                return Path(script_path)
        except (ImportError, FileNotFoundError):
            pass

    # Fallback to importlib_resources for Python 3.8
    try:
        import importlib_resources as resources
        with resources.as_file(
            resources.files(__package__).parent / "scripts" / script_name
        ) as script_path:
            return Path(script_path)
    except (ImportError, FileNotFoundError):
        pass

    # Final fallback for development mode or if resources don't work
    package_dir = Path(__file__).parent
    project_root = package_dir.parent
    return project_root / "scripts" / script_name

def get_go_launcher_script() -> Path:
    """Get the PowerShell launcher script path"""
    return get_script_path("go_launcher.ps1")

# Main API exports
from .go_launcher import GoLauncher
from .go_server import GoServer
from .go_thread import GoThread

__version__ = "0.1.0"
__author__ = "PyGoPS Team"
__description__ = "Python wrapper for Go applications with PowerShell launcher"

# Main API exports
__all__ = [
    # Main components
    "GoLauncher",
    "GoServer",
    "GoThread",

    # Utility functions
    "get_script_path",
    "get_go_launcher_script",
]