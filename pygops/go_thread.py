import subprocess
import threading
import json
from pathlib import Path
from subprocess import SubprocessError
from typing import Any, List
from loguru import logger as log


# noinspection PyUnboundLocalVariable
class GoThread(threading.Thread):
    """Ultra-lightweight thread that runs PowerShell with real-time output streaming"""

    def __init__(
        self, go_file: Path, script_path: Path, **kwargs: Any
    ):
        super().__init__(daemon=True)
        self.go_file = go_file
        self.script_path = script_path
        self.kwargs = kwargs
        self.verbose = kwargs.get('verbose', False)
        self._popen = None

        if self.verbose:
            props = "\n".join(f"{k}: {v}" for k, v in vars(self).items())
            log.success(f"{self}: Initialized GoThread with parameters:\n{props}")

    def _build_command(self) -> List[str]:
        """Build PowerShell command with proper parameter mapping"""

        ps1_path = Path(self.script_path).resolve()    # …/site-packages/pygops/scripts/go_launcher.ps1
        go_file  = Path(self.go_file).resolve()        # …/gosql/main.go

        cmd = [
            "powershell", "-ExecutionPolicy", "Bypass",
            "-File", str(ps1_path),
            "-GoFile", str(go_file)
        ]

        # Handle go_args - convert list to JSON string if provided
        go_args = self.kwargs.get('go_args', [])
        if isinstance(go_args, list):
            go_args_json = json.dumps(go_args)
        else:
            go_args_json = str(go_args) if go_args else "[]"

        cmd.extend(["-GoArgs", go_args_json])

        # Map old parameter names to new ones
        param_mapping = {
            'go_version': 'GoVersion',
            'force_go_install': 'ForceGoInstall',
            'is_server': 'ServerMode',
            'port': 'Port',
            'stop_existing': 'StopExisting',
            'dry_run': 'DryRun'
        }

        # Add parameters based on mapping
        for old_key, new_key in param_mapping.items():
            if old_key in self.kwargs:
                value = self.kwargs[old_key]
                if isinstance(value, bool):
                    if value:  # Only add switch if True
                        cmd.append(f"-{new_key}")
                else:
                    cmd.extend([f"-{new_key}", str(value)])

        # Add -Verbose if verbose is True
        if self.verbose:
            cmd.append("-Verbose")

        return cmd

    def _stream_output(self, pipe, prefix: str):
        """Stream output from a pipe in real-time"""
        try:
            for line in iter(pipe.readline, ''):
                if line.strip():
                    if self.verbose:
                        log.debug(f"[{prefix}]: {line.strip()}")
        except Exception as e:
            log.error(f"Error streaming {prefix}: {e}")
        finally:
            pipe.close()

    def run(self):
        """Run PowerShell script with real-time output streaming"""
        try:
            cmd = self._build_command()

            if self.verbose:
                log.debug(f"[GoThread] Running command: {' '.join(cmd)}")

            # Use the Go project directory as working directory
            go_dir = Path(self.go_file).parent.resolve()

            self._popen = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=str(go_dir),  # Run from Go project directory
                universal_newlines=True,
                bufsize=1  # Line buffered for real-time output
            )

            # Create threads for streaming stdout and stderr in real-time
            stdout_thread = threading.Thread(
                target=self._stream_output,
                args=(self._popen.stdout, "GO-OUT"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._stream_output,
                args=(self._popen.stderr, "GO-ERR"),
                daemon=True
            )

            # Start streaming threads
            stdout_thread.start()
            stderr_thread.start()

            # Wait for the process to complete
            ret = self._popen.wait()

            # Wait for streaming threads to finish
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

            if ret == 0:
                if self.verbose:
                    log.success(f"[GoThread] Process completed successfully")
            else:
                # Detailed error reporting
                exit_code_meanings = {
                    1: "General PowerShell error",
                    2: "Misuse of shell command",
                    126: "Command invoked cannot execute",
                    127: "Command not found",
                    128: "Invalid argument to exit",
                    130: "Script terminated by Ctrl+C",
                    4294770688: "Parameter binding error (likely invalid parameters)",
                    4294967295: "PowerShell execution policy restriction"
                }

                meaning = exit_code_meanings.get(ret, "Unknown error")

                log.error(f"[GoThread] PowerShell execution failed!")
                log.error(f"  Exit Code: {ret} ({meaning})")
                log.error(f"  Command: {' '.join(cmd)}")
                log.error(f"  Go File: {self.go_file}")
                log.error(f"  Script: {self.script_path}")
                log.error(f"  Working Directory: {go_dir}")

                # Specific suggestions based on exit code
                if ret == 4294770688:
                    log.error("  → This usually means invalid PowerShell parameters")
                    log.error("  → Check parameter names match the PowerShell script")
                    log.error(f"  → Parameters passed: {list(self.kwargs.keys())}")
                elif ret == 1:
                    log.error("  → Check if Go file exists and has correct permissions")
                    log.error("  → Verify PowerShell script syntax")
                elif ret == 4294967295:
                    log.error("  → PowerShell execution policy may be blocking script")
                    log.error("  → Try: Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser")
                
                # Don't raise exception for server processes that exit normally
                if not self.kwargs.get('is_server', False):
                    raise SubprocessError

        except FileNotFoundError:
            log.error(f"[GoThread] PowerShell not found - ensure PowerShell is installed")
            log.error(f"  Command attempted: {' '.join(cmd) if 'cmd' in locals() else 'N/A'}")
            raise FileNotFoundError
        except PermissionError:
            log.error(f"[GoThread] Permission denied executing PowerShell")
            log.error(f"  Script path: {self.script_path}")
            log.error(f"  Go file: {self.go_file}")
            raise PermissionError
        except Exception as e:
            log.error(f"[GoThread] Unexpected error during PowerShell execution: {e}")
            log.error(f"  Error type: {type(e).__name__}")
            log.error(f"  Command: {' '.join(cmd) if 'cmd' in locals() else 'N/A'}")
            raise Exception

    def terminate(self):
        """Terminate the running process if it exists"""
        if self._popen and self._popen.poll() is None:
            try:
                self._popen.terminate()
                log.debug("[GoThread] Process terminated")
            except Exception as e:
                log.error(f"Failed to terminate process: {e}")

    def is_running(self) -> bool:
        """Check if the process is still running"""
        return self._popen is not None and self._popen.poll() is None