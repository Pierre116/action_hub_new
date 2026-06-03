import os
from pathlib import Path

# Load .env from the same directory as this file (production deployments)
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from waitress import serve  # noqa: E402

from actionhub import create_app  # noqa: E402


app = create_app()


if __name__ == "__main__":
    host            = os.environ.get("HOST", "0.0.0.0")
    port            = int(os.environ.get("PORT", 5000))
    # 2-core VM: 4 threads is the sweet spot for I/O-bound Flask.
    # More threads = context-switch thrash, not more throughput.
    threads         = int(os.environ.get("THREADS", 4))
    channel_timeout = int(os.environ.get("CHANNEL_TIMEOUT", 30))
    print(f"ActionHub starting on http://{host}:{port}  (threads={threads})")
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        channel_timeout=channel_timeout,
        connection_limit=100,
        cleanup_interval=10,
        asyncore_loop_timeout=1,
    )
