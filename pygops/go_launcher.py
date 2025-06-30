import threading
import os
import shutil
from functools import cached_property
from pathlib import Path
from loguru import logger as log
from toomanyports import PortManager
from .go_thread import GoThread

class GoLauncher:
    """Ultra-lightweight launcher backed by PortManager for automatic port allocation and cleanup."""

    def __init__(self, go_file: Path, script_path: Path = None, **kwargs):
        self.go_file = Path(go_file)
        self.verbose = kwargs.get('verbose', False)
        
        # Discover script template location (same logic as GoServer)
        if script_path is None:
            script_dir = Path(__file__).parent / "scripts"
            script_path = script_dir / "go_launcher.ps1"
        
        self.original_script_path = Path(script_path)

        # Auto-copy script to Go project directory for proper working directory
        self.go_dir = self.go_file.parent
        self.script_path = self.go_dir / "go_launcher.ps1"
        
        self._ensure_local_script()

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
            log.debug(f"[GoLauncher] Go file: {self.go_file}")
            log.debug(f"[GoLauncher] Go directory: {self.go_dir}")
            log.debug(f"[GoLauncher] Original script: {self.original_script_path}")
            log.debug(f"[GoLauncher] Local script: {self.script_path}")
            log.debug(f"[GoLauncher] Local script exists: {self.script_path.exists()}")
            props = "\n".join(f"{k}: {v}" for k, v in vars(self).items())
            log.success(f"{self}: Initialized!\n{props}")

    def _ensure_local_script(self):
        """Copy PowerShell script to Go project directory if it doesn't exist or is outdated."""
        try:
            # Always copy to ensure we have the latest version
            if self.verbose:
                log.debug(f"[GoLauncher] Copying script from {self.original_script_path} to {self.script_path}")
            
            # Ensure Go directory exists
            self.go_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy script
            shutil.copy2(self.original_script_path, self.script_path)
            
            if self.verbose:
                log.debug(f"[GoLauncher] Successfully copied script to Go project directory")
                
        except Exception as e:
            log.error(f"[GoLauncher] Failed to copy script: {e}")
            # Fallback to original script path
            self.script_path = self.original_script_path
            if self.verbose:
                log.warning(f"[GoLauncher] Using original script path as fallback: {self.script_path}")

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

        # Spawn new GoThread with managed port and local script
        thr = GoThread(
            go_file=self.go_file,
            script_path=self.script_path,  # Use the local copy
            **self.kwargs
        )
        thr.name = name
        log.debug(f"[GoLauncher] launching {name} on port {self.kwargs['port']} from {self.go_dir}")
        return thr