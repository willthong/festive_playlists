"""De-festive run slice behind ``festive_playlists.defestive``."""

import logging

import pytest

CHRISTMAS_ID = "id-christmas"
BACKUP_ID = "id-backup-latest"
OLDER_BACKUP_ID = "id-backup-older"
BACKUP_NAME = "Favourites Backup 2025-12-24"

DISTINCT_CHRISTMAS_IDS = [f"xmas-{index:03d}" for index in range(120)]
CHRISTMAS_IDS = DISTINCT_CHRISTMAS_IDS + DISTINCT_CHRISTMAS_IDS[:7]
ALREADY_UNLIKED_IDS = ["xmas-003", "xmas-050", "xmas-119"]
LIKED_CHRISTMAS_IDS = [
    track_id for track_id in DISTINCT_CHRISTMAS_IDS if track_id not in ALREADY_UNLIKED_IDS
]
PRE_EXISTING_LIKE_IDS = ["xmas-001", "xmas-002", "xmas-100"]
# Only in the older Favourites Backup, so never a pre-existing like for this run.
OLDER_BACKUP_ONLY_IDS = ["xmas-004", "other-old"]
BACKUP_TRACK_IDS = PRE_EXISTING_LIKE_IDS + ["other-1", "other-2"]


class FakeSpotify:
    """Stand-in for the ``spotipy.Spotify`` calls a de-festive run makes."""

    def __init__(
        self,
        *,
        playlists: list[tuple[str, str]],
        playlist_tracks: dict[str, list[str]],
        liked_ids: list[str],
        playlist_page_size: int = 2,
        items_page_size: int = 30,
    ) -> None:
        self._playlists = list(playlists)
        self._playlist_tracks = playlist_tracks
        self._liked_ids = set(liked_ids)
        self._playlist_page_size = playlist_page_size
        self._items_page_size = items_page_size
        self.delete_calls: list[list[str]] = []
        self.save_calls: list[list[str]] = []
        self.other_mutations: list[str] = []

    @staticmethod
    def _page(
        items: list[dict[str, object]],
        offset: int,
        page_size: int,
    ) -> dict[str, object]:
        next_offset = offset + page_size
        return {
            "items": items[offset:next_offset],
            "next": (
                f"https://api.spotify.com/v1/next?offset={next_offset}"
                if next_offset < len(items)
                else None
            ),
        }

    def current_user_playlists(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        items = [
            {"id": playlist_id, "name": name} for name, playlist_id in self._playlists
        ]
        return self._page(items, offset, self._playlist_page_size)

    def playlist_items(
        self,
        playlist_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, object]:
        ids = self._playlist_tracks.get(playlist_id)
        assert ids is not None, playlist_id
        items = [{"track": {"id": track_id}} for track_id in ids]
        return self._page(items, offset, self._items_page_size)

    def current_user_saved_tracks_contains(self, tracks: list[str]) -> list[bool]:
        return [track_id in self._liked_ids for track_id in tracks]

    def current_user_saved_tracks_delete(self, tracks: list[str]) -> None:
        self.delete_calls.append(list(tracks))
        self._liked_ids -= set(tracks)

    def current_user_saved_tracks_add(self, tracks: list[str]) -> None:
        self.save_calls.append(list(tracks))

    def user_playlist_create(
        self,
        user: str,
        name: str,
        public: bool = True,
        description: str = "",
    ) -> dict[str, object]:
        self.other_mutations.append(f"create {name}")
        return {"id": "unexpected", "name": name}

    def playlist_add_items(self, playlist_id: str, items: list[str]) -> dict[str, str]:
        self.other_mutations.append(f"add to {playlist_id}")
        return {"snapshot_id": "unexpected"}

    def playlist_remove_all_occurrences_of_items(
        self,
        playlist_id: str,
        items: list[str],
    ) -> dict[str, str]:
        self.other_mutations.append(f"remove from {playlist_id}")
        return {"snapshot_id": "unexpected"}


def _warnings(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    )


def test_defestive_run_unlikes_christmas_playlist_and_flags_unexpected_cases(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dry run plans; the real run unlikes Christmas tracks and warns."""
    from festive_playlists.defestive import run

    monkeypatch.delenv("SPOTIFY_CHRISTMAS_PLAYLIST_ID", raising=False)
    sp = FakeSpotify(
        playlists=[
            ("Christmas", CHRISTMAS_ID),
            ("Road Trip", "id-trip"),
            (BACKUP_NAME, BACKUP_ID),
            ("Favourites Backup 2024-12-24", OLDER_BACKUP_ID),
        ],
        playlist_tracks={
            CHRISTMAS_ID: CHRISTMAS_IDS,
            BACKUP_ID: BACKUP_TRACK_IDS,
            OLDER_BACKUP_ID: OLDER_BACKUP_ONLY_IDS,
        },
        liked_ids=LIKED_CHRISTMAS_IDS,
    )

    plan = run(sp, dry_run=True)

    assert sorted(plan.track_ids) == DISTINCT_CHRISTMAS_IDS
    assert sorted(plan.pre_existing_like_ids) == PRE_EXISTING_LIKE_IDS
    assert sp.delete_calls == [], "a dry run must not unlike anything"
    assert sp.save_calls == [], "a dry run must not touch Liked Songs"
    assert sp.other_mutations == [], sp.other_mutations

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        run(sp)

    assert [len(batch) for batch in sp.delete_calls] == [50, 50, 17]
    deleted = [track_id for batch in sp.delete_calls for track_id in batch]
    assert sorted(deleted) == LIKED_CHRISTMAS_IDS
    for track_id in ALREADY_UNLIKED_IDS:
        assert track_id not in deleted, track_id
    assert sp.save_calls == [], "the de-festive run must not restore the backup"
    assert sp.other_mutations == [], sp.other_mutations

    text = _warnings(caplog)
    assert "pre-existing" in text.lower(), text
    for track_id in PRE_EXISTING_LIKE_IDS:
        assert track_id in text, text

    monkeypatch.setenv("SPOTIFY_CHRISTMAS_PLAYLIST_ID", "id-lower")
    caplog.clear()
    ambiguous = FakeSpotify(
        playlists=[
            ("Christmas", "id-capital"),
            ("christmas", "id-lower"),
            (BACKUP_NAME, "id-backup"),
        ],
        playlist_tracks={
            "id-capital": ["capital-1", "capital-2"],
            "id-lower": ["lower-1", "lower-2"],
            "id-backup": ["normal-1"],
        },
        liked_ids=["capital-1", "capital-2", "lower-1", "lower-2"],
    )

    with caplog.at_level(logging.WARNING):
        ambiguous_plan = run(ambiguous)

    assert sorted(ambiguous_plan.track_ids) == ["lower-1", "lower-2"]
    assert ambiguous_plan.pre_existing_like_ids == []
    deleted = [track_id for batch in ambiguous.delete_calls for track_id in batch]
    assert sorted(deleted) == ["lower-1", "lower-2"]

    text = _warnings(caplog)
    assert "christmas" in text.lower(), text
    assert "id-lower" in text or "SPOTIFY_CHRISTMAS_PLAYLIST_ID" in text, text
