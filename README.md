# PyGoPS

## What Happens

1. **Python**: All kwargs flow through 3 tiny components
2. **PowerShell**: Splits kwargs into:
   - **Launcher config**: `verbose`, `check_ports`, `force_go_install`, etc.
   - **Go arguments**: Everything else becomes `go run -arg value`

## Launcher vs Go Arguments

### Launcher Config (hardcoded in PowerShell)
- `force_go_install` - Force Go installation
- `go_version` - Go version to install  
- `check_ports` - Check port availability
- `stop_existing` - Stop conflicting processes
- `background` - Run in background
- `timeout_seconds` - Process timeout
- `verbose` - Enable logging

### Go Arguments (pure passthrough)
- `port=8080` → `go run -port 8080`
- `debug=True` → `go run -debug`
- `config="app.json"` → `go run -config app.json`
- `database_url="..."` → `go run -database_url ...`
- **Any kwarg** → **Go flag**

## Examples

```python
from pygops import GoServer

GoServer(port=8080)
# Runs: go run -port 8080

# Complex server
GoServer(
    port=8080,
    host="0.0.0.0",
    database_url="postgres://localhost/db",
    redis_url="redis://localhost:6379",
    log_level="debug",
    enable_metrics=True,
    jwt_secret="secret",
    # Launcher config
    verbose=True,
    check_ports=True
)
# Runs: go run -port 8080 -host 0.0.0.0 -database_url postgres://localhost/db -redis_url redis://localhost:6379 -log_level debug -enable_metrics -jwt_secret secret

# Working directory is wherever you run Python from
GoServer(project_dir="./my-app", port=3000)
# Changes to ./my-app and runs: go run -project_dir ./my-app -port 3000
```

Perfect separation: Python handles async, PowerShell handles launcher concerns, everything else is pure Go arguments!