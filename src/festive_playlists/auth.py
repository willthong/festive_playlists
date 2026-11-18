"""Spotify authentication: refresh-token grant behind an authenticated client."""

import time
from collections.abc import Mapping

import requests
import spotipy

TOKEN_URL = "https://accounts.spotify.com/api/token"

REQUIRED_SECRETS = (
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REFRESH_TOKEN",
)

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 1.0


def _read_secrets(env: Mapping[str, str]) -> dict[str, str]:
    """Return the required secrets, or fail before any network call."""
    missing = [name for name in REQUIRED_SECRETS if not env.get(name)]
    if missing:
        raise ValueError(f"missing required secrets: {', '.join(missing)}")
    return {name: env[name] for name in REQUIRED_SECRETS}


def _retry_delay(response: requests.Response, attempt: int) -> float:
    """Honour Retry-After when present, otherwise use exponential backoff."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return BASE_BACKOFF_SECONDS * 2**attempt


def _refresh_access_token(secrets: Mapping[str, str]) -> str:
    """Exchange the refresh token for an access token, retrying on 429/5xx."""
    for attempt in range(MAX_ATTEMPTS):
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": secrets["SPOTIFY_REFRESH_TOKEN"],
            },
            auth=(secrets["SPOTIFY_CLIENT_ID"], secrets["SPOTIFY_CLIENT_SECRET"]),
            timeout=30,
        )
        transient = response.status_code == 429 or response.status_code >= 500
        if transient and attempt < MAX_ATTEMPTS - 1:
            time.sleep(_retry_delay(response, attempt))
            continue
        if response.status_code != 200:
            raise ValueError(f"token request failed with HTTP {response.status_code}")
        access_token = response.json().get("access_token")
        if not access_token:
            raise ValueError("token response did not include an access_token")
        return str(access_token)
    raise ValueError("token request failed after retries")


def get_client(env: Mapping[str, str]) -> spotipy.Spotify:
    """Build an authenticated Spotify client from the CI secrets in ``env``."""
    secrets = _read_secrets(env)
    return spotipy.Spotify(auth=_refresh_access_token(secrets))
