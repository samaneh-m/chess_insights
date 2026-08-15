"""Exceptions raised by the Chess.com integration.

Raw ``httpx`` exceptions never escape ``ChessComClient`` as its public
API -- they're always caught and re-raised as one of these, chained via
``raise ... from exc`` so the original cause is preserved for debugging.
"""


class ChessComError(Exception):
    """Base class for all Chess.com integration errors."""


class ChessComUserNotFoundError(ChessComError):
    """The requested Chess.com username does not exist (HTTP 404)."""


class ChessComRateLimitError(ChessComError):
    """Chess.com responded with 429 Too Many Requests."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ChessComAPIError(ChessComError):
    """Chess.com responded with an unexpected error status (4xx/5xx)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ChessComConnectionError(ChessComError):
    """The request to Chess.com failed at the network/transport level."""


class ChessComDataError(ChessComError):
    """A Chess.com response (archive list or game record) could not be parsed."""
