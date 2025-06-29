from functools import cached_property
from pathlib import Path
from .go_thread import GoThread


class GoLauncher:
    """Ultra-lightweight launcher - just creates threads"""

    def __init__(self, script_path: Path, **kwargs):
        self.script_path = script_path
        self.kwargs = kwargs

    @cached_property
    def thread(self):
        """Create a thread that runs PowerShell script with kwargs"""
        return GoThread(script_path=self.script_path, **self.kwargs)