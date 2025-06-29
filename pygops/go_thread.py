import subprocess
import threading
from pathlib import Path
from typing import Any
from loguru import logger as log


class GoThread(threading.Thread):
    """Ultra-lightweight thread that runs PowerShell with kwargs"""

    def __init__(self, script_path: Path, **kwargs):
        super().__init__(daemon=True)
        self.script_path = script_path
        self.kwargs = kwargs
        self.verbose = kwargs.get('verbose', False)
        self._popen = None

    def run(self):
        """Run PowerShell script with all kwargs as parameters"""
        cmd = [
            "powershell", "-ExecutionPolicy", "Bypass",
            "-File", str(self.script_path)
        ]

        # Convert all kwargs to PowerShell parameters
        for key, value in self.kwargs.items():
            if isinstance(value, bool):
                if value:  # Only add flag if True
                    cmd.append(f"-{key}")
            else:
                cmd.extend([f"-{key}", str(value)])

        if self.verbose:
            log.debug(f"Running: {' '.join(cmd)}")

        try:
            self._popen = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if self.verbose:
                for line in self._popen.stdout:
                    log.debug(f"[PS]: {line.strip()}")

            self._popen.wait()

        except Exception as e:
            log.error(f"PowerShell execution failed: {e}")