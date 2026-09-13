"""Structured logging setup.

Call `configure_logging()` once, at process startup (see `app/main.py`). This
configures structlog's own loggers only — third-party libraries that log via
stdlib `logging` (uvicorn, SQLAlchemy's `echo=True`) are not routed through it
yet. Unifying the two is real work (P7 Observability); out of scope here.
"""

import logging

import structlog


def configure_logging(*, debug: bool) -> None:
    # Human-readable, colored output while developing; one JSON object per line
    # everywhere else, because that's what a log aggregator actually consumes.
    renderer: structlog.types.Processor = (
        structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            # Pulls in whatever `structlog.contextvars.bind_contextvars(...)`
            # set for the current task — this is how `request_id` gets onto
            # every log line without threading it through every function call.
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
