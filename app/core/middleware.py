"""Request-id propagation and access logging.

Deliberately a *pure* ASGI middleware (a plain class with `__call__`), not
`starlette.middleware.base.BaseHTTPMiddleware`. BaseHTTPMiddleware runs the
downstream app in a separate anyio task, which silently breaks contextvars
propagation — the request_id bound below would not appear on log lines
emitted further down the stack. Pure ASGI middleware runs in the same task as
everything it wraps, so structlog's contextvars work as expected.
"""

import time
import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger("app.request")


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _get_header(scope, b"x-request-id") or str(uuid.uuid4())
        # Cleared first: contextvars survive across requests on the same task
        # in some ASGI servers' connection-keep-alive paths, so a stale
        # request_id from a previous request must not leak into this one.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers: list[tuple[bytes, bytes]] = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        method: Any = scope["method"]
        path: Any = scope["path"]
        start = time.perf_counter()
        logger.info("request_started", method=method, path=path)
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("request_failed", method=method, path=path)
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_finished",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )


def _get_header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode()
    return None
