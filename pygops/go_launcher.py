import threading
import os
from functools import cached_property
from pathlib import Path
from loguru import logger as log
from toomanyports import PortManager
from .go_thread import GoThread

class GoLauncher:
    """Ultra-lightweight launcher backed by PortManager for automatic port allocation and cleanup."""

    def __init__(self, go_file: str, script_path: Path, **kwargs):
        self.go_file = go_file
        self.script_path = script_path
        self.verbose = kwargs.get('verbose', False)

        # Setup PortManager
        pm = PortManager()
        port = kwargs.get('port')
        if port:
            pm.kill(port)
        else:
            port = pm.random_port()
        kwargs['port'] = port
        self.kwargs = kwargs

        if self.verbose:
            props = "\n".join(f"{k}: {v}" for k, v in vars(self).items())
            log.success(f"{self}: Initialized!\n{props}")

    @cached_property
    def thread(self):
        # Name thread after go file base name
        name = Path(self.go_file).name

        # Clean up any old GoThread instances
        for t in threading.enumerate():
            if isinstance(t, GoThread) and t.name == name and t.is_alive():
                log.debug(f"[GoLauncher] stopping old thread {name}")
                t.stop()
                t.join(timeout=1)

        # Spawn new GoThread with managed port
        thr = GoThread(
            go_file=self.go_file,
            script_path=self.script_path,
            **self.kwargs
        )
        thr.name = name
        log.debug(f"[GoLauncher] launching {name} on port {self.kwargs['port']}")
        return thr
