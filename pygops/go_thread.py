import subprocess
import threading
import json
from pathlib import Path
from subprocess import SubprocessError
from typing import Any, List
from loguru import logger as log


class GoThread(threading.Thread):
    """Ultra-lightweight thread that runs PowerShell with kwargs"""

    def __init__(
        self, go_file: str, script_path: Path, **kwargs: Any
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

    def run(self):
        """Run PowerShell script with all kwargs as parameters"""
        stdout_lines = []
        stderr_lines = []

        try:
            cmd = self._build_command()

            if self.verbose:
                log.debug(f"[GoThread] Running command: {' '.join(cmd)}")

            cwd = Path(self.script_path).parent.resolve()        # …/gosql/main.go

            self._popen = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Keep stderr separate for better error analysis
                text=True,
                encoding='utf-8',  # Explicitly set encoding to avoid cp1252 issues
                errors='replace',  # Replace problematic characters instead of crashing
                cwd=str(cwd),  # Run from script directory
                universal_newlines=True
            )

            # Use communicate() to properly capture both stdout and stderr
            stdout_output, stderr_output = self._popen.communicate()

            # Process stdout
            if stdout_output and stdout_output.strip():
                stdout_lines = stdout_output.strip().split('\n')
                if self.verbose:
                    for line in stdout_lines:
                        if line.strip():
                            log.debug(f"[PS]: {line.strip()}")

            # Process stderr
            if stderr_output and stderr_output.strip():
                stderr_lines = stderr_output.strip().split('\n')
                if self.verbose:
                    for line in stderr_lines:
                        if line.strip():
                            log.debug(f"[PS-ERR]: {line.strip()}")

            self._popen.wait()
            ret = self._popen.returncode

            if ret == 0:
                if self.verbose:
                    log.success(f"[GoThread] Process completed successfully")
            else:
                # Detailed error reporting
                error_context = {
                    "exit_code": ret,
                    "command": ' '.join(cmd),
                    "go_file": self.go_file,
                    "script_path": str(self.script_path),
                    "kwargs": self.kwargs
                }

                # Common PowerShell exit codes
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

                if stderr_lines:
                    log.error("  STDERR Output:")
                    for line in stderr_lines:
                        log.error(f"    {line}")

                if stdout_lines:
                    log.error("  Last STDOUT Output:")
                    # Show last few lines of stdout for context
                    for line in stdout_lines[-10:]:
                        log.error(f"    {line}")

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
            if stdout_lines:
                log.error("  Captured output before error:")
                for line in stdout_lines[-5:]:
                    log.error(f"    {line}")
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