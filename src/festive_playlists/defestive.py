"""De-festive run: unlike the Christmas Playlist and flag unexpected cases."""

import logging
import os
from dataclasses import dataclass

import spotipy

from festive_playlists.festive import _batches, _track_ids
from festive_playlists.playlists import (
    most_recent_backup,
    resolve_christmas_playlist,
)

BATCH_SIZE = 50
PLAYLIST_PAGE_SIZE = 100

logger = logging.getLogger(__name__)


@dataclass
class DeFestivePlan:
    """What a de-festive run does: tracks to unlike and pre-existing likes."""

    track_ids: list[str]
    pre_existing_like_ids: list[str]


def run(
    sp: spotipy.Spotify,
    dry_run: bool = False,
) -> DeFestivePlan:
    """Unlike every track in the Christmas Playlist, unless dry running."""
    christmas_id = resolve_christmas_playlist(
        sp, os.environ.get("SPOTIFY_CHRISTMAS_PLAYLIST_ID")
    )
    christmas_tracks = _track_ids(
        lambda limit, offset: sp.playlist_items(
            christmas_id, limit=limit, offset=offset
        ),
        PLAYLIST_PAGE_SIZE,
    )
    track_ids = list(dict.fromkeys(christmas_tracks))

    backup_id = most_recent_backup(sp)
    backup_tracks: list[str] = []
    if backup_id is None:
        logger.warning(
            "no Favourites Backup found; cannot flag pre-existing likes"
        )
    else:
        backup_tracks = _track_ids(
            lambda limit, offset: sp.playlist_items(
                backup_id, limit=limit, offset=offset
            ),
            PLAYLIST_PAGE_SIZE,
        )
    backup_set = set(backup_tracks)
    pre_existing = [track_id for track_id in track_ids if track_id in backup_set]

    plan = DeFestivePlan(
        track_ids=track_ids,
        pre_existing_like_ids=pre_existing,
    )
    if dry_run:
        return plan

    liked_tracks: list[str] = []
    for batch in _batches(track_ids, BATCH_SIZE):
        contains = sp.current_user_saved_tracks_contains(batch)
        liked_tracks.extend(
            track_id
            for track_id, is_liked in zip(batch, contains)
            if is_liked
        )

    for batch in _batches(liked_tracks, BATCH_SIZE):
        for track_id in batch:
            if track_id in backup_set:
                logger.warning("pre-existing like being removed: %s", track_id)
        sp.current_user_saved_tracks_delete(batch)
    return plan
