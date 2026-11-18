"""Get a Spotify refresh token with the authorization-code flow.

Run this on your own machine. It starts a local callback server, opens the
Spotify consent page, and writes the refresh token to a file.
"""

import argparse
import base64
import http.server
import json
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

REDIRECT_URI = "http://127.0.0.1:8080/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = (
    "user-library-read",
    "user-library-modify",
    "playlist-read-private",
    "playlist-modify-private",
)

PAGE = """<!doctype html>
<title>Festive Playlists</title>
<h1>{heading}</h1>
<p>{message}</p>
"""


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handle the one callback request from Spotify."""

    expected_state = ""
    code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/callback":
            self._reply(404, "Not found", "This is not the callback path.")
            return
        if params.get("state", [""])[0] != self.expected_state:
            self.error = "state mismatch"
            self._reply(400, "State mismatch", "Close this tab and try again.")
            return
        if "error" in params:
            self.error = params["error"][0]
            self._reply(400, "Authorization failed", self.error)
            return
        self.code = params.get("code", [None])[0]
        self._reply(200, "Authorized", "You can close this tab now.")

    def _reply(self, status: int, heading: str, message: str) -> None:
        body = PAGE.format(heading=heading, message=message).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        """Silence the default request logging."""


def _exchange_code(client_id: str, client_secret: str, code: str) -> str:
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
    ).encode()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    token = payload.get("refresh_token")
    if not token:
        raise RuntimeError("Spotify did not return a refresh token")
    return str(token)


def _authorize(client_id: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id", default=os.environ.get("SPOTIFY_CLIENT_ID"))
    parser.add_argument(
        "--client-secret", default=os.environ.get("SPOTIFY_CLIENT_SECRET")
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the refresh token here instead of printing it.",
    )
    args = parser.parse_args()
    if not args.client_id or not args.client_secret:
        parser.error("--client-id and --client-secret are required")

    state = secrets.token_urlsafe(16)
    CallbackHandler.expected_state = state
    url = _authorize(args.client_id, state)
    print(f"Opening Spotify authorization page:\n{url}\n")
    webbrowser.open(url)

    server = http.server.HTTPServer(("127.0.0.1", 8080), CallbackHandler)
    print("Waiting for the callback on 127.0.0.1:8080 ...")
    server.handle_request()
    if CallbackHandler.code is None:
        raise SystemExit(f"Authorization failed: {CallbackHandler.error}")

    token = _exchange_code(args.client_id, args.client_secret, CallbackHandler.code)
    if args.output:
        args.output.write_text(token)
        args.output.chmod(0o600)
        print(f"Refresh token saved to {args.output}")
    else:
        print(token)


if __name__ == "__main__":
    main()
