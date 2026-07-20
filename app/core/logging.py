import json
import logging
import sys


class _JsonFormatter(logging.Formatter):
    """
    Renders each log record as one JSON line:
    {"event": "...", "level": "...", <structured fields...>}

    Structured logs are far easier to grep/filter/aggregate than free-text
    messages, especially once request_id becomes a standard field present
    on every log line for a given request.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {"event": record.getMessage(), "level": record.levelname}
        payload.update(getattr(record, "structured_fields", {}))
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure the "app" logger to emit structured JSON lines to stdout.
    Call once at startup (see app/main.py). Idempotent - safe to call
    more than once (e.g. across repeated test runs) without stacking up
    duplicate handlers and double-logging every event.
    """
    logger = logging.getLogger("app")
    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False  # don't also send these up to the root logger


def get_logger() -> logging.Logger:
    """Retrieve the app's configured logger."""
    return logging.getLogger("app")


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """
    Emit one structured log line for `event`, with `fields` as
    structured data - e.g. request_id, retrieval_mode,
    retrieved_chunk_count, attempt, retrieval_ms, generation_ms.

    Deliberately takes explicit keyword fields rather than a free-form
    dict or the whole request/response object. This is where "never log
    API keys, full prompts, or full document contents" actually gets
    enforced - callers can only log what they explicitly name here, not
    an entire object that might contain sensitive content by accident.

    NEVER pass: api_key, prompt, question text, document text/content.
    Fine to pass: request_id, retrieval_mode, chunk counts, chunk IDs,
    attempt numbers, timings, status.
    """
    logger.info(event, extra={"structured_fields": fields})