"""Auth slice: refresh-token flow behind ``festive_playlists.auth.get_client``."""

import json

import pytest
import requests
import spotipy

TOKEN_URL = "https://accounts.spotify.com/api/token"
ACCESS_TOKEN = "fresh-access-token"


def _env() -> dict[str, str]:
    return {
        "SPOTIFY_CLIENT_ID": "test-client-id",
        "SPOTIFY_CLIENT_SECRET": "test-client-secret",
        "SPOTIFY_REFRESH_TOKEN": "test-refresh-token",
    }


def _token_response(
    status: int,
    body: dict[str, object],
    headers: dict[str, str] | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = TOKEN_URL
    response.headers["Content-Type"] = "application/json"
    response.headers.update(headers or {})
    response._content = json.dumps(body).encode("utf-8")
    return response


def test_get_client_refreshes_after_429_and_rejects_missing_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from festive_playlists.auth import get_client

    token_responses = [
        _token_response(429, {"error": "rate_limited"}, {"Retry-After": "0"}),
        _token_response(
            200,
            {"access_token": ACCESS_TOKEN, "token_type": "Bearer", "expires_in": 3600},
        ),
    ]
    token_posts: list[str] = []

    def fake_token_post(url: str, *args: object, **kwargs: object) -> requests.Response:
        token_posts.append(url)
        assert token_responses, "token refresh retried after a successful response"
        return token_responses.pop(0)

    monkeypatch.setattr(requests, "post", fake_token_post)
    monkeypatch.setattr(requests.Session, "post", fake_token_post)

    incomplete = _env()
    del incomplete["SPOTIFY_REFRESH_TOKEN"]
    with pytest.raises(ValueError, match="SPOTIFY_REFRESH_TOKEN"):
        get_client(incomplete)
    assert token_posts == [], "missing secrets must fail before any token request"

    client = get_client(_env())

    assert isinstance(client, spotipy.Spotify)
    assert token_posts == [TOKEN_URL, TOKEN_URL], token_posts
