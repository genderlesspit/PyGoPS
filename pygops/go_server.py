import asyncio
import time
from pathlib import Path
from typing import Optional
from loguru import logger as log

from .go_launcher import GoLauncher


class GoServer:
    """Ultra-lightweight Go server manager"""

    def __init__(self, go_file: Path, script_path: Optional[Path] = None, **kwargs):
        self.go_file = go_file
        self.kwargs = kwargs
        self.verbose = kwargs.get('verbose', False)

        script_dir = Path(__file__).parent / "scripts"  # files are now under pygops/scripts
        ps1_path   = script_dir / "go_launcher.ps1"
        self.script_path = script_path or ps1_path

        if self.verbose:
            log.debug(f"[GoServer] Script path: {self.script_path}")
            log.debug(f"[GoServer] Script exists: {self.script_path.exists()}")

        server_kwargs = {"is_server": True, **kwargs}
        self._launcher = GoLauncher(go_file, self.script_path, **server_kwargs)

        if self.verbose:
            props = "\n".join(f"{k}: {v}" for k, v in vars(self).items())
            log.success(f"{self} Successfully initialized!\n{props}")

    def __repr__(self):
        return f"[PyGoPS.GoServer]"

    @property
    def url(self) -> str:
        port = self.kwargs.get('port', 3000)
        return f"http://localhost:{port}"

    async def start(self):
        if self._launcher.thread.is_alive():
            if self.verbose:
                log.debug(f"{self}: already running")
            return

        self._launcher.thread.start()
        time.sleep(3)

    async def is_running(self) -> bool:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/health", timeout=1) as r:
                    return r.status < 500
        except:
            return False

    async def stop(self):
        if hasattr(self._launcher.thread, '_popen'):
            if self._launcher.thread._popen and self._launcher.thread._popen.poll() is None:
                await asyncio.to_thread(self._launcher.thread._popen.terminate)
                await asyncio.to_thread(self._launcher.thread._popen.wait)

    def get_status(self) -> dict:
        return {
            "url": self.url,
            "running": self._launcher.thread.is_alive(),
            "kwargs": self.kwargs,
            "script_path": str(self.script_path),
            "script_exists": self.script_path.exists()
        }