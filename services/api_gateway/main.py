"""Uvicorn entrypoint.

Run locally (after `docker compose ... up -d`):

    uv run python -m services.api_gateway.main

The Gateway expects Postgres, Keycloak, and the OTel collector reachable.
"""

from __future__ import annotations

import asyncio
import selectors
import sys

import uvicorn

from services.api_gateway.app import create_app

app = create_app()

if __name__ == '__main__':
    # Windows ProactorEventLoop is incompatible with psycopg async mode.
    # uvicorn.run() internally uses asyncio.Runner which ignores
    # set_event_loop_policy() — so we create a SelectorEventLoop manually
    # and run the server against it.
    if sys.platform == 'win32':
        _loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(_loop)

        config = uvicorn.Config(app, host='0.0.0.0', port=8051, log_level='info')
        server = uvicorn.Server(config)
        try:
            _loop.run_until_complete(server.serve())
        finally:
            _loop.close()
    else:
        uvicorn.run(app, host='0.0.0.0', port=8051)
