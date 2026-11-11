"""Extractor no oficial de datos de fútbol de SofaScore."""

from __future__ import annotations

__version__ = "1.15.2"

from .client import ClientConfig, SofaScoreClient  # noqa: E402
from .exceptions import (  # noqa: E402
    BlockedError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    SofaScoreError,
)
from .extractor import SofaScoreExtractor  # noqa: E402

__all__ = [
    "__version__",
    "ClientConfig",
    "SofaScoreClient",
    "SofaScoreExtractor",
    "SofaScoreError",
    "NotFoundError",
    "BlockedError",
    "RateLimitError",
    "NetworkError",
]
