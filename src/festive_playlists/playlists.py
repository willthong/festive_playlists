"""Christmas Playlist and Favourites Backup resolution."""

import logging
from datetime import date

import spotipy

CHRISTMAS_PLAYLIST_NAME = "Christmas"
FAVOURITES_BACKUP_PREFIX = "Favourites Backup"

_PAGE_SIZE = 50

logger = logging.getLogger(__name__)


def _user_playlists(sp: spotipy.Spotify) -> list[tuple[str, str]]:
    """Return every (name, id) pair for the current user's playlists."""
    playlists: list[tuple[str, str]] = []
    offset = 0
    while True:
        page = sp.current_user_playlists(limit=_PAGE_SIZE, offset=offset)
        items = page.get("items") or []
        for item in items:
            playlists.append((str(item.get("name", "")), str(item.get("id", ""))))
        if not page.get("next") or not items:
            return playlists
        offset += len(items)


def resolve_christmas_playlist(
    sp: spotipy.Spotify,
    christmas_id: str | None = None,
) -> str:
    """Return the id of the Christmas Playlist, disambiguating when needed."""
    target = CHRISTMAS_PLAYLIST_NAME.lower()
    matches = [
        playlist_id
        for name, playlist_id in _user_playlists(sp)
        if name.lower() == target
    ]
    if not matches:
        raise ValueError("no playlist named Christmas found")
    if len(matches) == 1:
        return matches[0]
    if christmas_id is None:
        raise ValueError(
            "multiple playlists named Christmas; set SPOTIFY_CHRISTMAS_PLAYLIST_ID"
        )
    logger.warning(
        "multiple playlists named Christmas; using SPOTIFY_CHRISTMAS_PLAYLIST_ID"
    )
    return christmas_id


def find_or_create_backup(sp: spotipy.Spotify, today: date) -> str:
    """Return today's Favourites Backup id, creating it privately if needed."""
    name = f"{FAVOURITES_BACKUP_PREFIX} {today.isoformat()}"
    for existing_name, playlist_id in _user_playlists(sp):
        if existing_name == name:
            return playlist_id
    created = sp.current_user_playlist_create(name, public=False)
    return str(created["id"])


def most_recent_backup(sp: spotipy.Spotify) -> str | None:
    """Return the id of the most recent Favourites Backup, if any."""
    latest: tuple[date, str] | None = None
    for name, playlist_id in _user_playlists(sp):
        if not name.startswith(f"{FAVOURITES_BACKUP_PREFIX} "):
            continue
        try:
            backup_date = date.fromisoformat(
                name.removeprefix(f"{FAVOURITES_BACKUP_PREFIX} ").strip()
            )
        except ValueError:
            continue
        if latest is None or backup_date > latest[0]:
            latest = (backup_date, playlist_id)
    return latest[1] if latest is not None else None
