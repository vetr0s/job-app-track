"""The web frontend: a second frontend over the same Store the CLI uses.

serve() opens one Store, runs migrations, and blocks in the HTTP loop until
Ctrl-C. Route handlers live in routes.py; transport in http.py and server.py.
"""

from __future__ import annotations

from pathlib import Path

from ..core import Store
from .server import make_server

__all__ = ["serve"]


def serve(db_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> int:
    with Store.open(db_path) as store:
        httpd = make_server(host, port, store)
        print(f"job-app-track serving on http://{host}:{port}  (db: {db_path})")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
        finally:
            httpd.server_close()
    return 0
