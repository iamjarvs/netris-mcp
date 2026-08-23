"""
Low-level HTTP helpers for the Netris REST API.

All functions accept a pre-authenticated httpx.AsyncClient (created in
server.py's lifespan) and return parsed JSON dicts.  Non-2xx responses
raise RuntimeError with a consistent message so tool code can catch a
single exception type.

URL construction
----------------
Use ``api_url()`` to build well-formed Netris v2 endpoint URLs:

    api_url(base_url, "bgp")              → https://host/api/v2/bgp/
    api_url(base_url, "bgp", 42)          → https://host/api/v2/bgp/42
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Payload keys whose values must never be written to logs, even at DEBUG.
_SENSITIVE_KEYS = {"password", "bgppassword", "secret", "token"}


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``data`` with sensitive values masked for logging."""
    return {
        k: ("***" if k.lower() in _SENSITIVE_KEYS else v)
        for k, v in data.items()
    }


# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------


def api_url(base_url: str, resource: str, resource_id: int | None = None) -> str:
    """
    Build a versioned Netris API URL.

    Parameters
    ----------
    base_url:
        Controller base URL including scheme, e.g. ``https://netris.example.com``.
        Trailing slashes are stripped automatically.
    resource:
        API resource path segment, e.g. ``"bgp"``, ``"vpc"``, ``"ipam/subnets"``.
    resource_id:
        Optional integer ID.  When provided the URL ends with ``/{resource_id}``
        (no trailing slash).  When absent the URL ends with a trailing slash to
        match Netris's canonical collection URL form.

    Returns
    -------
    str
        Fully qualified URL string.

    Examples
    --------
    >>> api_url("https://ctrl.example.com", "vpc")
    'https://ctrl.example.com/api/v2/vpc/'
    >>> api_url("https://ctrl.example.com", "vpc", 7)
    'https://ctrl.example.com/api/v2/vpc/7'
    """
    base = base_url.rstrip("/")
    resource = resource.strip("/")
    if resource_id is not None:
        return f"{base}/api/v2/{resource}/{resource_id}"
    return f"{base}/api/v2/{resource}/"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _raise_for_status(response: httpx.Response) -> None:
    """Raise RuntimeError for non-2xx responses with a descriptive message."""
    if response.status_code not in range(200, 300):
        raise RuntimeError(
            f"Netris API error {response.status_code}: {response.text}"
        )


def _parse_json(response: httpx.Response) -> dict[str, Any]:
    """
    Parse JSON from a response.

    Returns an empty dict when the body is empty (e.g. 204 No Content) so
    callers always get a dict back and don't need to handle None.
    """
    if not response.content:
        return {}
    try:
        return response.json()
    except Exception as exc:
        raise RuntimeError(
            f"Netris API returned non-JSON body "
            f"(HTTP {response.status_code}): {response.text[:300]}"
        ) from exc


# ---------------------------------------------------------------------------
# HTTP verbs
# ---------------------------------------------------------------------------


async def get(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    """
    Perform a GET request and return the parsed JSON response body.

    Parameters
    ----------
    client:
        Authenticated httpx.AsyncClient.
    url:
        Full URL to request (use ``api_url()`` to build it).

    Returns
    -------
    dict
        Parsed JSON response.

    Raises
    ------
    RuntimeError
        On non-2xx HTTP status or non-JSON response body.
    """
    logger.debug("GET %s", url)
    try:
        response = await client.get(url)
    except httpx.RequestError as exc:
        raise RuntimeError(f"GET {url} failed: {exc}") from exc

    _raise_for_status(response)
    return _parse_json(response)


async def post(client: httpx.AsyncClient, url: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Perform a POST request with a JSON body and return the parsed JSON response.

    Parameters
    ----------
    client:
        Authenticated httpx.AsyncClient.
    url:
        Full URL to request.
    data:
        Request body; will be serialised to JSON.

    Returns
    -------
    dict
        Parsed JSON response.

    Raises
    ------
    RuntimeError
        On non-2xx HTTP status or non-JSON response body.
    """
    logger.debug("POST %s payload=%s", url, _redact(data))
    try:
        response = await client.post(url, json=data)
    except httpx.RequestError as exc:
        raise RuntimeError(f"POST {url} failed: {exc}") from exc

    _raise_for_status(response)
    return _parse_json(response)


async def put(client: httpx.AsyncClient, url: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Perform a PUT request with a JSON body and return the parsed JSON response.

    Parameters
    ----------
    client:
        Authenticated httpx.AsyncClient.
    url:
        Full URL to request.
    data:
        Request body; will be serialised to JSON.

    Returns
    -------
    dict
        Parsed JSON response.

    Raises
    ------
    RuntimeError
        On non-2xx HTTP status or non-JSON response body.
    """
    logger.debug("PUT %s payload=%s", url, _redact(data))
    try:
        response = await client.put(url, json=data)
    except httpx.RequestError as exc:
        raise RuntimeError(f"PUT {url} failed: {exc}") from exc

    _raise_for_status(response)
    return _parse_json(response)


async def delete(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    """
    Perform a DELETE request and return the parsed JSON response body.

    Parameters
    ----------
    client:
        Authenticated httpx.AsyncClient.
    url:
        Full URL to request (typically includes the resource ID).

    Returns
    -------
    dict
        Parsed JSON response, or an empty dict for 204 No Content.

    Raises
    ------
    RuntimeError
        On non-2xx HTTP status or non-JSON response body.
    """
    logger.debug("DELETE %s", url)
    try:
        response = await client.delete(url)
    except httpx.RequestError as exc:
        raise RuntimeError(f"DELETE {url} failed: {exc}") from exc

    _raise_for_status(response)
    return _parse_json(response)
