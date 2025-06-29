import asyncio
import time
from pathlib import Path

from pygops import GoServer

async def test_advanced():
    path = Path.cwd() / "scripts" / "go_dummy.go"
    server = GoServer(str(path), port=8080, verbose=True)
    await server.start()

    if await server.is_running():
        print(f"✓ Advanced server running at {server.url}")
        print(f"✓ Config endpoint: {server.url}/config")
        print(f"✓ Metrics endpoint: {server.url}/metrics")
        print(f"✓ Echo endpoint: {server.url}/echo")

        # Check status
        status = server.get_status()
        print(f"✓ Status: {status}")

    await server.stop()

asyncio.run(test_advanced())