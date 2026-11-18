"""Festive run: back up Liked Songs, then like the Christmas Playlist."""

import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

import spotipy

from festive_playlists.playlists import (
    FAVOURITES_BACKUP_PREFIX,
    find_or_create_backup,
    resolve_christmas_playlist,
)

LIKED_PAGE_SIZE = 50
PLAYLIST_PAGE_SIZE = 50
BACKUP_BATCH_SIZE = 100
LIKE_BATCH_SIZE = 50

PageFetcher = Callable[..., dict[str, Any]]


@dataclass
class FestivePlan:
    """What a festive run does: today's backup name and tracks to like."""

    backup_name: str
    track_ids: list[str]


def _page_track_ids(items: list[dict[str, Any]]) -> list[str]:
    """Return the track ids on one page, tolerating the legacy ``track`` key.

    Spotify's February 2026 Web API rename moved playlist entries from
    ``item.track`` to ``item.item``; ``track`` is kept as a fallback.
    """
    track_ids: list[str] = []
    for item in items:
        track = item.get("item") or item.get("track") or {}
        track_id = track.get("id")
        if track_id:
            track_ids.append(str(track_id))
    return track_ids


def _track_ids(fetch: PageFetcher, page_size: int) -> list[str]:
    """Collect every track id from a paginated Spotify collection."""
    track_ids: list[str] = []
    offset = 0
    while True:
        page = fetch(limit=page_size, offset=offset)
        items = page.get("items")
        if items is None:
            raise ValueError(
                "Spotify returned no items list; playlist contents are only "
                "available for playlists you own or collaborate on"
            )
        page_ids = _page_track_ids(items)
        if items and not page_ids:
            raise ValueError(
                "Spotify returned items with no track objects; expected "
                "'item' (or legacy 'track') to hold an id"
            )
        track_ids.extend(page_ids)
        if not page.get("next") or not items:
            return track_ids
        offset += len(items)


def _batches(track_ids: list[str], size: int) -> Iterator[list[str]]:
    """Yield ``track_ids`` in batches of at most ``size``."""
    for start in range(0, len(track_ids), size):
        yield track_ids[start : start + size]


def run(
    sp: spotipy.Spotify,
    today: date,
    dry_run: bool = False,
) -> FestivePlan:
    """Back up Liked Songs and like the Christmas Playlist, unless dry running."""
    backup_name = f"{FAVOURITES_BACKUP_PREFIX} {today.isoformat()}"
    christmas_id = resolve_christmas_playlist(
        sp, os.environ.get("SPOTIFY_CHRISTMAS_PLAYLIST_ID")
    )
    christmas_tracks = _track_ids(
        lambda limit, offset: sp.playlist_items(
            christmas_id, limit=limit, offset=offset
        ),
        PLAYLIST_PAGE_SIZE,
    )

    plan = FestivePlan(
        backup_name=backup_name,
        track_ids=list(dict.fromkeys(christmas_tracks)),
    )
    if dry_run:
        return plan

    backup_id = find_or_create_backup(sp, today)
    liked_tracks = _track_ids(
        lambda limit, offset: sp.current_user_saved_tracks(
            limit=limit, offset=offset
        ),
        LIKED_PAGE_SIZE,
    )
    for batch in _batches(liked_tracks, BACKUP_BATCH_SIZE):
        sp.playlist_add_items(backup_id, batch)
    for batch in _batches(plan.track_ids, LIKE_BATCH_SIZE):
        sp.current_user_saved_tracks_add(batch)
    return plan
