"""
Configuration loader for the Netris MCP server.

Reads all settings from environment variables (with .env file support).
Call get_config() once at startup; the result is a plain dataclass so it
can be passed around freely without coupling to this module.
"""

import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NetrisConfig:
    """Immutable configuration snapshot read from the environment."""

    host: str
    """Netris controller hostname or IP, without scheme (e.g. 'netris.example.com')."""

    username: str
    """Netris login username."""

    password: str
    """Netris login password."""

    ssl_verify: bool
    """Whether to verify the controller's TLS certificate (default True)."""

    session_refresh_seconds: int
    """How often (in seconds) to ping the API to keep the session alive (default 1800)."""

    timeout: float
    """Per-request HTTP timeout in seconds (default 30.0)."""


def get_config() -> NetrisConfig:
    """
    Load configuration from environment variables, optionally sourced from a
    .env file in the current working directory.

    Required variables
    ------------------
    NETRIS_HOST       Hostname / IP of the Netris controller (no scheme)
    NETRIS_USERNAME   Login username
    NETRIS_PASSWORD   Login password

    Optional variables
    ------------------
    NETRIS_SSL_VERIFY        "false" or "0" disables TLS verification (default: true)
    NETRIS_SESSION_REFRESH   Keep-alive interval in seconds             (default: 1800)
    NETRIS_TIMEOUT           Per-request timeout in seconds             (default: 30.0)

    Raises
    ------
    ValueError
        If any required variable is absent or empty.
    """
    load_dotenv()

    missing: list[str] = []

    host = os.environ.get("NETRIS_HOST", "").strip()
    if not host:
        missing.append("NETRIS_HOST")

    username = os.environ.get("NETRIS_USERNAME", "").strip()
    if not username:
        missing.append("NETRIS_USERNAME")

    password = os.environ.get("NETRIS_PASSWORD", "").strip()
    if not password:
        missing.append("NETRIS_PASSWORD")

    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Set them directly or place them in a .env file."
        )

    # --- optional fields with safe defaults ---

    ssl_verify_raw = os.environ.get("NETRIS_SSL_VERIFY", "true").strip().lower()
    ssl_verify = ssl_verify_raw not in ("false", "0", "no", "off")

    try:
        session_refresh_seconds = int(os.environ.get("NETRIS_SESSION_REFRESH", "1800").strip())
        if session_refresh_seconds < 60:
            logger.warning(
                "NETRIS_SESSION_REFRESH is very short (%d s); using 60 s minimum.",
                session_refresh_seconds,
            )
            session_refresh_seconds = 60
    except ValueError:
        raise ValueError(
            "NETRIS_SESSION_REFRESH must be an integer number of seconds, "
            f"got: {os.environ.get('NETRIS_SESSION_REFRESH')!r}"
        )

    try:
        timeout = float(os.environ.get("NETRIS_TIMEOUT", "30.0").strip())
        if timeout <= 0:
            raise ValueError("timeout must be positive")
    except ValueError:
        raise ValueError(
            "NETRIS_TIMEOUT must be a positive number of seconds, "
            f"got: {os.environ.get('NETRIS_TIMEOUT')!r}"
        )

    if not ssl_verify:
        logger.warning(
            "TLS certificate verification is DISABLED (NETRIS_SSL_VERIFY=false). "
            "Only use this in trusted lab environments."
        )

    return NetrisConfig(
        host=host,
        username=username,
        password=password,
        ssl_verify=ssl_verify,
        session_refresh_seconds=session_refresh_seconds,
        timeout=timeout,
    )
