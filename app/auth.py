"""
Authentication helpers for the Netris API.

Netris uses cookie-based session auth exclusively.  The login endpoint
returns a Set-Cookie header containing ``connect.sid``.  We extract the
full cookie jar and hand it to the long-lived httpx.AsyncClient so every
subsequent request is automatically authenticated.

No API keys, no JWT, no Bearer headers — just cookies.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


async def login(
    host: str,
    username: str,
    password: str,
    ssl_verify: bool = True,
) -> dict[str, str]:
    """
    Authenticate against the Netris controller and return the session cookies.

    Opens a short-lived httpx.AsyncClient (separate from the main one) solely
    for the login request, then closes it immediately.  The caller should store
    the returned cookies on the long-lived client.

    Parameters
    ----------
    host:
        Controller hostname or IP without scheme, e.g. ``netris.example.com``.
    username:
        Netris login username.
    password:
        Netris login password.
    ssl_verify:
        Whether to verify the controller's TLS certificate.

    Returns
    -------
    dict[str, str]
        A mapping of cookie names to values.  Always contains at least
        ``connect.sid`` on a successful login.

    Raises
    ------
    RuntimeError
        If the HTTP request fails or the server returns a non-2xx status.
    """
    url = f"https://{host}/api/v2/auth/login"
    payload = {"login": username, "password": password}

    logger.info("Logging in to Netris controller at %s", url)

    try:
        async with httpx.AsyncClient(verify=ssl_verify, timeout=30.0) as tmp_client:
            response = await tmp_client.post(url, json=payload)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot reach Netris controller at {host!r}: {exc}. "
            "Check NETRIS_HOST and network connectivity."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Timed out connecting to Netris controller at {host!r}: {exc}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"HTTP request to {url} failed: {exc}"
        ) from exc

    if response.status_code not in range(200, 300):
        # Avoid leaking credentials in the log — only show the status code and
        # the sanitised response body.
        body_preview = response.text[:300].replace(password, "***")
        raise RuntimeError(
            f"Netris login failed with HTTP {response.status_code}. "
            f"Check NETRIS_USERNAME / NETRIS_PASSWORD. "
            f"Response body: {body_preview}"
        )

    cookies: dict[str, str] = dict(response.cookies)

    if "connect.sid" not in cookies:
        logger.warning(
            "Login succeeded (HTTP %d) but 'connect.sid' cookie was not found. "
            "Cookie jar: %s",
            response.status_code,
            list(cookies.keys()),
        )
    else:
        logger.info(
            "Successfully authenticated to Netris (HTTP %d); session cookie obtained.",
            response.status_code,
        )

    return cookies


async def refresh_session(client: httpx.AsyncClient, host: str) -> None:
    """
    Keep the Netris session alive by hitting the profile endpoint.

    This is a best-effort call — transient failures (e.g. a brief network
    hiccup) are logged as warnings and swallowed rather than propagated, so
    the background refresh loop continues running.  If the session has
    genuinely expired the next real API call will surface a 401 error with a
    clearer message.

    Parameters
    ----------
    client:
        The authenticated long-lived httpx.AsyncClient.
    host:
        Controller hostname or IP without scheme.
    """
    url = f"https://{host}/api/v2/auth/profile"
    logger.debug("Refreshing Netris session via GET %s", url)

    try:
        response = await client.get(url)
        if response.status_code in range(200, 300):
            logger.debug("Session refresh succeeded (HTTP %d).", response.status_code)
        elif response.status_code == 401:
            logger.warning(
                "Session refresh returned HTTP 401 — session may have expired. "
                "The next API call will surface this as an error."
            )
        else:
            logger.warning(
                "Session refresh returned unexpected HTTP %d. "
                "Session may still be valid; continuing.",
                response.status_code,
            )
    except httpx.TimeoutException:
        logger.warning(
            "Session refresh timed out (GET %s). "
            "Will retry on the next interval.",
            url,
        )
    except httpx.RequestError as exc:
        logger.warning(
            "Session refresh request error (GET %s): %s. "
            "Will retry on the next interval.",
            url,
            exc,
        )
