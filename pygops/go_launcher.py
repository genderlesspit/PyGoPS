from functools import cached_property
from pathlib import Path
from .go_thread import GoThread
from loguru import logger as log


class GoLauncher:
    """Ultra-lightweight launcher - just creates threads"""

    def __init__(self, go_file: str, script_path: Path, **kwargs):
        self.go_file = go_file
        self.script_path = script_path
        self.kwargs = kwargs
        self.verbose = kwargs.get('verbose', False)

        if self.verbose:
            props = "\n".join(f"{k}: {v}" for k, v in vars(self).items())
            log.success(f"{self}: Successfully initialized!\n{props}")

    @cached_property
    def thread(self):
        """Create a thread that runs PowerShell script with kwargs"""
        return GoThread(go_file=self.go_file, script_path=self.script_path, **self.kwargs)
