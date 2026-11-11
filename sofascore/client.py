"""Cliente HTTP para la API interna de SofaScore.

SofaScore protege su API con Cloudflare y comprueba la huella TLS del
cliente. Por eso se usa ``curl_cffi`` con impersonación de Chrome y se
realiza una petición previa a la web para obtener cookies válidas.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from . import endpoints
from .exceptions import (
    BlockedError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    SofaScoreError,
)

_MISSING = object()


def xrw_token(now: Optional[float] = None) -> str:
    """Token efímero que SofaScore exige en ``X-Requested-With``.

    El sitio calcula ``SHA-256`` del bloque de 30 minutos actual y usa sus
    seis primeros caracteres. No es una firma secreta, pero cambia cada
    media hora y algunos filtros de Varnish lo comprueban.
    """
    bucket = int((time.time() if now is None else now) // 1800)
    return hashlib.sha256(str(bucket).encode("ascii")).hexdigest()[:6]


def default_cache_dir() -> Path:
    """Devuelve un directorio de caché adecuado para el sistema."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "sofascore-extractor" / "cache"


@dataclass
class ClientConfig:
    base_url: str = "https://www.sofascore.com/api/v1"
    timeout: float = 30.0
    rate_limit: float = 0.2
    retries: int = 4
    backoff: float = 1.5
    use_cache: bool = True
    cache_dir: Path = field(default_factory=default_cache_dir)
    cache_ttl: int = 300
    proxy: Optional[str] = None
    impersonate: str = "chrome"
    force_ipv4: bool = True
    debug: bool = False
    dump_raw: Optional[Path] = None


class RateLimiter:
    """Espacia las peticiones entre todos los hilos."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = max(0.0, float(min_interval))
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_at - now)
            self._next_at = max(now, self._next_at) + self.min_interval
        if delay:
            time.sleep(delay)

    def penalize(self, seconds: float) -> None:
        """Pausa globalmente tras un 403/429."""
        with self._lock:
            self._next_at = max(self._next_at, time.monotonic() + max(0.0, seconds))


class _SessionPool:
    """Una sesión curl_cffi por hilo, con cookies propias."""

    def __init__(self, config: ClientConfig, limiter: RateLimiter) -> None:
        self.config = config
        self.limiter = limiter
        self._local = threading.local()
        self._interface_lock = threading.Lock()
        # SofaScore/Varnish devuelve «403 challenge» a muchas conexiones IPv6.
        # curl_cffi prefiere IPv6 cuando el DNS lo ofrece, así que forzamos
        # IPv4 y volvemos al comportamiento del sistema solo si falla.
        self._ipv4 = bool(config.force_ipv4)

    def get(self):
        session = getattr(self._local, "session", None)
        if session is None:
            session = self._create_session()
            self._local.session = session
        return session

    def reset(self) -> None:
        session = getattr(self._local, "session", None)
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        self._local.session = None

    def interface(self) -> Optional[str]:
        with self._interface_lock:
            return "0.0.0.0" if self._ipv4 else None

    def disable_ipv4(self) -> None:
        with self._interface_lock:
            self._ipv4 = False

    def _create_session(self):
        try:
            from curl_cffi import requests as curl_requests
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise SofaScoreError(
                "Falta la dependencia 'curl_cffi'. Instálala con:\n"
                "    pip install -r requirements.txt\n"
                "SofaScore bloquea clientes con huella TLS de Python estándar."
            ) from exc

        session = curl_requests.Session(impersonate=self.config.impersonate)

        # Petición previa a la web: obtiene cookies de Cloudflare.
        self.limiter.wait()
        try:
            warmup_kwargs: Dict[str, Any] = {
                "headers": {
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,"
                        "image/avif,image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                },
                "timeout": min(self.config.timeout, 20),
                "proxies": self._proxies(),
            }
            interface = self.interface()
            if interface is not None:
                warmup_kwargs["interface"] = interface
            session.get("https://www.sofascore.com/", **warmup_kwargs)
        except Exception:
            # Si la web falla, intentamos la API de todos modos.
            pass
        return session

    def _proxies(self) -> Optional[Dict[str, str]]:
        if not self.config.proxy:
            return None
        return {"http": self.config.proxy, "https": self.config.proxy}


class SofaScoreClient:
    """Cliente con reintentos, caché en disco y limitación de ritmo."""

    def __init__(self, config: Optional[ClientConfig] = None) -> None:
        self.config = config or ClientConfig()
        self._limiter = RateLimiter(self.config.rate_limit)
        self._sessions = _SessionPool(self.config, self._limiter)
        self._cache_ok = bool(self.config.use_cache and self._prepare_cache())
        self._write_lock = threading.Lock()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def get_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> Any:
        """Descarga y devuelve el JSON de ``path``.

        ``ttl`` permite sobreescribir el tiempo de vida de la caché para
        una petición concreta. ``ttl=0`` evita la caché.
        """
        effective_ttl = self._ttl_for(ttl)
        key = self._cache_key(path, params)

        if self._cache_ok and effective_ttl > 0:
            cached = self._cache_read(key, effective_ttl)
            if cached is not _MISSING:
                if self.config.debug:
                    self._debug(f"CACHE {path}")
                return cached

        data = self._request(path, params)

        if self._cache_ok and effective_ttl > 0:
            self._cache_write(key, data)
        return data

    # ------------------------------------------------------------------
    # Petición HTTP
    # ------------------------------------------------------------------
    def _request(self, path: str, params: Optional[Dict[str, Any]]) -> Any:
        url = self.config.base_url.rstrip("/") + path
        attempts = max(1, int(self.config.retries) + 1)
        last_error: Optional[BaseException] = None

        for attempt in range(attempts):
            self._limiter.wait()
            interface = self._sessions.interface()
            try:
                session = self._sessions.get()
                request_kwargs: Dict[str, Any] = {
                    "params": params,
                    "headers": self._headers(),
                    "timeout": self.config.timeout,
                    "proxies": self._sessions._proxies(),
                }
                if interface is not None:
                    request_kwargs["interface"] = interface
                response = session.get(url, **request_kwargs)
            except SofaScoreError:
                raise
            except Exception as exc:
                last_error = exc
                if interface is not None:
                    # La ruta IPv4 no está disponible: volvemos a la del sistema.
                    self._sessions.disable_ipv4()
                    if self.config.debug:
                        self._debug(
                            f"IPv4 no disponible ({exc!r}); usando la ruta del sistema."
                        )
                    if attempt < attempts - 1:
                        continue
                if self.config.debug:
                    self._debug(f"NETWORK {url} -> {exc!r}")
                if attempt < attempts - 1:
                    self._sleep(attempt)
                    continue
                raise NetworkError(
                    f"No se pudo conectar con SofaScore: {exc}"
                ) from exc

            status = int(response.status_code)
            body = response.content or b""
            if self.config.debug:
                self._debug(f"GET {url} -> {status} ({len(body)} bytes)")

            if self.config.dump_raw:
                self._dump_raw(path, status, body)

            if status == 200:
                if not body:
                    if attempt < attempts - 1:
                        self._sleep(attempt)
                        continue
                    raise NetworkError(
                        "SofaScore devolvió una respuesta vacía (200). "
                        "Prueba a esperar unos minutos o usa un proxy."
                    )
                try:
                    return response.json()
                except ValueError as exc:
                    raise NetworkError(
                        "La respuesta de SofaScore no es JSON válido. "
                        "Puede tratarse de un bloqueo o de un cambio de API."
                    ) from exc

            if status == 404:
                raise NotFoundError(
                    f"Recurso no encontrado (404): {endpoints.with_params(path, params)}"
                )

            if status == 403:
                last_error = BlockedError(
                    "SofaScore devolvió 403 (challenge de Cloudflare). "
                    "Espera unos minutos, baja --rate-limit o usa --proxy. "
                    "Si el navegador te pide verificar que eres humano, "
                    "ábrelo en sofascore.com y completa la verificación."
                )
                self._limiter.penalize(4.0 + attempt * 2.0)
                self._sessions.reset()
                if attempt < attempts - 1:
                    self._sleep(attempt)
                    continue
                raise last_error

            if status == 429:
                last_error = RateLimitError(
                    "SofaScore devolvió 429 (demasiadas peticiones). "
                    "Aumenta --rate-limit (por ejemplo 0.5 o 1.0)."
                )
                self._limiter.penalize(10.0 + attempt * 5.0)
                if attempt < attempts - 1:
                    self._sleep(attempt, response)
                    continue
                raise last_error

            if 500 <= status < 600:
                last_error = SofaScoreError(
                    f"Error del servidor de SofaScore (HTTP {status})."
                )
                if attempt < attempts - 1:
                    self._sleep(attempt, response)
                    continue
                raise last_error

            snippet = body[:200].decode("utf-8", errors="replace")
            raise SofaScoreError(f"HTTP {status} en {url}: {snippet}")

        raise last_error or SofaScoreError(f"No se pudo completar la petición: {url}")

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com",
            "X-Requested-With": xrw_token(),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def _sleep(self, attempt: int, response: Any = None) -> None:
        wait = min(30.0, self.config.backoff * (2 ** attempt) + random.uniform(0, 0.5))
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            try:
                if retry_after:
                    wait = min(60.0, max(wait, float(retry_after)))
            except (TypeError, ValueError):
                pass
        if self.config.debug:
            self._debug(f"ESPERA {wait:.1f}s (intento {attempt + 2})")
        time.sleep(wait)

    # ------------------------------------------------------------------
    # Caché
    # ------------------------------------------------------------------
    def _ttl_for(self, ttl: Optional[int]) -> int:
        if ttl is None:
            return int(self.config.cache_ttl)
        return int(ttl)

    def _prepare_cache(self) -> bool:
        try:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as exc:
            if self.config.debug:
                self._debug(f"No se pudo crear la caché: {exc}")
            return False

    def _cache_key(self, path: str, params: Optional[Dict[str, Any]]) -> str:
        payload = path
        if params:
            payload += "?" + json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.config.cache_dir / f"{key}.json"

    def _cache_read(self, key: str, ttl: int) -> Any:
        path = self._cache_path(key)
        try:
            with path.open("r", encoding="utf-8") as fh:
                wrapper = json.load(fh)
            created = float(wrapper["created"])
            if time.time() - created > ttl:
                return _MISSING
            return wrapper["data"]
        except FileNotFoundError:
            return _MISSING
        except (OSError, ValueError, KeyError, TypeError):
            try:
                path.unlink()
            except OSError:
                pass
            return _MISSING

    def _cache_write(self, key: str, data: Any) -> None:
        path = self._cache_path(key)
        wrapper = {"created": time.time(), "data": data}
        tmp = path.with_suffix(
            f".{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp"
        )
        try:
            with self._write_lock:
                with tmp.open("w", encoding="utf-8") as fh:
                    json.dump(wrapper, fh, ensure_ascii=False)
                os.replace(tmp, path)
        except OSError as exc:
            if self.config.debug:
                self._debug(f"No se pudo escribir la caché: {exc}")
            try:
                tmp.unlink()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Depuración
    # ------------------------------------------------------------------
    def _debug(self, message: str) -> None:
        print(f"[sofascore] {message}", file=sys.stderr)

    def _dump_raw(self, path: str, status: int, body: bytes) -> None:
        if not self.config.dump_raw:
            return
        try:
            self.config.dump_raw.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^A-Za-z0-9]+", "_", path).strip("_")[:80] or "root"
            digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]
            filename = (
                f"{time.strftime('%Y%m%d_%H%M%S')}_{slug}_{digest}_{status}.json"
            )
            (self.config.dump_raw / filename).write_bytes(body)
        except OSError as exc:
            if self.config.debug:
                self._debug(f"No se pudo guardar la respuesta cruda: {exc}")
