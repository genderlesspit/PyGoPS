import asyncio
from pygops import GoServer

async def test_advanced():
    server = GoServer(
        # Go server arguments
        port=8080,
        host="0.0.0.0",
        database_url="postgres://user:pass@localhost/testdb",
        redis_url="redis://localhost:6379",
        log_level="debug",
        jwt_secret="super-secret-key-12345",
        debug=True,
        enable_cors=True,
        enable_metrics=True,
        max_connections=50,
        verbose=True,
        check_ports=True,
        force_go_install=True
    )

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