# pygops

Python wrapper for running Go applications via PowerShell.

```bash
pip install pygops
```

## Requirements

* Python 3.8 or higher
* PowerShell installed and accessible in PATH
* Go installed for running Go applications
* Dependencies (installed automatically):

  * `loguru`
  * `toomanyports`
  * `aiohttp` (for server health checks)

## Usage

### Launch a Go script manually

```python
from pygops import GoLauncher

launcher = GoLauncher(
    go_file="path/to/script.go",
    script_path=script_path,
    verbose=True,
    port=5000  # optional: will kill existing or choose random if omitted
)
launcher.thread.start()
```

### Run a Go server with health check

```python
import asyncio
from pygops import GoServer, get_go_launcher_script

script = get_go_launcher_script()
server = GoServer(
    go_file="path/to/main.go",
    script_path=script,
    port=4000,
    verbose=True
)

async def main():
    await server.start()
    running = await server.is_running()
    print(f"Server running: {running}")
    # ... later ...
    await server.stop()

asyncio.run(main())
```

### Execute Go script in its own thread

```python
from pygops import GoThread, get_go_launcher_script

thread = GoThread(
    go_file="path/to/task.go",
    script_path=get_go_launcher_script(),
    go_args=["--flag", "value"],
    verbose=True
)
thread.start()
# Do other work...
if thread.is_running():
    thread.terminate()
```

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.
