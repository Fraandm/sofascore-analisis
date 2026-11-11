"""Excepciones propias del extractor."""

from __future__ import annotations


class SofaScoreError(Exception):
    """Error base del extractor."""


class NotFoundError(SofaScoreError):
    """El recurso no existe en la API (HTTP 404)."""


class BlockedError(SofaScoreError):
    """SofaScore/Cloudflare ha bloqueado la petición (HTTP 403)."""


class RateLimitError(SofaScoreError):
    """Se ha superado el límite de peticiones (HTTP 429)."""


class NetworkError(SofaScoreError):
    """Error de red, timeout o respuesta no válida."""
