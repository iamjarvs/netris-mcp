"""Asynchronous HTTP client for the Netris Controller REST APIs.

Features:
- Handles both v1 (/api/...) and v2 (/api/v2/...) endpoints seamlessly.
- Cookie-based session management (`connect.sid`).
- Automatic re-login on 401 Unauthorized.
- Exponential backoff retry logic for idempotent operations on 5xx errors or network glitches.
- Standard Netris envelope unwrapping: raises NetrisAPIError when isSuccess is False.
- Automatic redaction of sensitive credentials in debug logs.
- Safe pagination helper with configurable safety bounds.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {"password", "bgppassword", "bgp_password", "secret", "token", "connect.sid"}


def redact(data: Any) -> Any:
    """Mask sensitive keys in dicts/lists for safe debug logging."""
    if isinstance(data, dict):
        return {
            k: ("***" if any(s in k.lower() for s in _SENSITIVE_KEYS) else redact(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [redact(item) for item in data]
    return data


class NetrisAPIError(Exception):
    """Raised when the Netris Controller returns an error status or isSuccess: false."""

    def __init__(self, status_code: int, message: str, errors: Any = None):
        super().__init__(f"Netris API Error [{status_code}]: {message}")
        self.status_code = status_code
        self.message = message
        self.errors = errors


class NetrisClient:
    """Synchronous / Asynchronous capable HTTP Client for Netris Controller."""

    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        verify_ssl: bool = False,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._authenticated = False

    async def get_client(self) -> httpx.AsyncClient:
        """Initialise or return existing AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close client session cleanly."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            self._authenticated = False

    async def login(self) -> bool:
        """Authenticate with the controller and establish the connect.sid session cookie."""
        client = await self.get_client()
        payload = {
            "user": self.username,
            "password": self.password,
            "auth_schema_key": "local",
        }
        logger.debug("Attempting login to Netris controller at %s", self.base_url)
        try:
            res = await client.post("/api/auth", json=payload)
            if res.status_code == 200:
                self._authenticated = True
                logger.info("Successfully authenticated to Netris controller")
                return True
            else:
                logger.error("Authentication failed: HTTP %s - %s", res.status_code, res.text)
                self._authenticated = False
                return False
        except Exception as e:
            logger.error("Authentication request error: %s", e)
            self._authenticated = False
            raise

    async def request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        json_data: Any = None,
        retries: int = 2,
    ) -> Any:
        """Execute HTTP request with session re-auth and backoff retries."""
        client = await self.get_client()
        if not self._authenticated and path != "/api/auth":
            await self.login()

        url_path = path if path.startswith("/") else f"/{path}"

        for attempt in range(retries + 1):
            try:
                res = await client.request(
                    method=method,
                    url=url_path,
                    params=params,
                    json=json_data,
                )

                # If session timed out (401), re-login once and retry
                if res.status_code == 401 and attempt == 0 and path != "/api/auth":
                    logger.warning("Received 401 Unauthorized. Refreshing session...")
                    logged_in = await self.login()
                    if logged_in:
                        continue

                # Server error retry with backoff for idempotent GET requests
                if method.upper() == "GET" and res.status_code >= 500 and attempt < retries:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning(
                        "HTTP %s on %s. Retrying in %.2fs (attempt %d/%d)...",
                        res.status_code,
                        url_path,
                        backoff,
                        attempt + 1,
                        retries,
                    )
                    await asyncio.sleep(backoff)
                    continue

                if res.status_code >= 400:
                    try:
                        err_json = res.json()
                        msg = err_json.get("message") or res.text
                        errs = err_json.get("errors")
                    except Exception:
                        msg = res.text
                        errs = None
                    raise NetrisAPIError(res.status_code, msg, errs)

                try:
                    body = res.json()
                except Exception:
                    return res.text

                # Handle Netris envelope
                if isinstance(body, dict) and "isSuccess" in body:
                    if not body.get("isSuccess", False):
                        raise NetrisAPIError(
                            res.status_code,
                            body.get("message", "API reported isSuccess: false"),
                            body.get("errors"),
                        )
                    return body.get("data")

                return body

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if method.upper() == "GET" and attempt < retries:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning("Network/Timeout error on %s: %s. Retrying in %.2fs...", url_path, e, backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise

    # -------------------------------------------------------------------------
    # Convenience HTTP Methods
    # -------------------------------------------------------------------------

    async def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json_data: Any = None) -> Any:
        return await self.request("POST", path, json_data=json_data)

    async def put(self, path: str, json_data: Any = None) -> Any:
        return await self.request("PUT", path, json_data=json_data)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)

    # -------------------------------------------------------------------------
    # Pagination Helper
    # -------------------------------------------------------------------------

    async def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        page_size: int = 50,
        max_items: int = 1000,
    ) -> list[Any]:
        """Automatically traverse paginated endpoints with a strict upper bound safety cap."""
        items: list[Any] = []
        page = 1
        query = dict(params or {})

        while len(items) < max_items:
            query["page"] = page
            query["limit"] = page_size

            data = await self.get(path, params=query)

            if not data or not isinstance(data, list):
                break

            items.extend(data)

            if len(data) < page_size:
                # Reached final page
                break

            page += 1

        return items[:max_items]
