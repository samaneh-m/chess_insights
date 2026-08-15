"""Exceptions raised by the Lichess integration.

Raw ``httpx`` exceptions never escape ``LichessClient`` as its public
API -- they're always caught and re-raised as one of these, chained via
``raise ... from exc`` so the original cause is preserved for debugging.
"""


class LichessError(Exception):
    """Base class for all Lichess integration errors."""


class LichessUserNotFoundError(LichessError):
    """The requested Lichess username does not exist (HTTP 404)."""


class LichessRateLimitError(LichessError):
    """Lichess responded with 429 Too Many Requests."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LichessAPIError(LichessError):
    """Lichess responded with an unexpected error status (4xx/5xx)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LichessConnectionError(LichessError):
    """The request to Lichess failed at the network/transport level."""


class LichessDataError(LichessError):
    """A Lichess response record could not be parsed/normalized."""
