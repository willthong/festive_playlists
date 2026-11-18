"""Festive run slice behind ``festive_playlists.festive``."""

from datetime import date

import pytest

TODAY = date(2025, 12, 24)
CHRISTMAS_ID = "id-christmas"
BACKUP_NAME = "Favourites Backup 2025-12-24"

LIKED_IDS = [f"liked-{index:03d}" for index in range(250)]
DISTINCT_CHRISTMAS_IDS = [f"xmas-{index:03d}" for index in range(120)]
CHRISTMAS_IDS = DISTINCT_CHRISTMAS_IDS + DISTINCT_CHRISTMAS_IDS[:10]


class FakeSpotify:
    """Paginating stand-in for the ``spotipy.Spotify`` calls a festive run makes."""

    def __init__(
        self,
        *,
        liked_ids: list[str],
        christmas_ids: list[str],
        playlist_page_size: int = 2,
        liked_page_size: int = 40,
        items_page_size: int = 30,
    ) -> None:
        self._playlists = [("Christmas", CHRISTMAS_ID)]
        self._liked_ids = liked_ids
        self._christmas_ids = christmas_ids
        self._playlist_page_size = playlist_page_size
        self._liked_page_size = liked_page_size
        self._items_page_size = items_page_size
        self.create_calls: list[dict[str, object]] = []
        self.add_calls: list[tuple[str, list[str]]] = []
        self.like_calls: list[list[str]] = []
        self._next_id = 1

    @staticmethod
    def _page(
        items: list[dict[str, object]],
        offset: int,
        page_size: int,
    ) -> dict[str, object]:
        page = items[offset : offset + page_size]
        next_offset = offset + page_size
        return {
            "items": page,
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
            {"id": playlist_id, "name": name}
            for name, playlist_id in self._playlists
        ]
        return self._page(items, offset, self._playlist_page_size)

    def current_user_saved_tracks(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        items = [{"track": {"id": track_id}} for track_id in self._liked_ids]
        return self._page(items, offset, self._liked_page_size)

    def playlist_items(
        self,
        playlist_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, object]:
        assert playlist_id == CHRISTMAS_ID, playlist_id
        items = [{"item": {"id": track_id}} for track_id in self._christmas_ids]
        return self._page(items, offset, self._items_page_size)

    def current_user_playlist_create(
        self,
        name: str,
        public: bool = True,
        collaborative: bool = False,
        description: str = "",
    ) -> dict[str, object]:
        playlist_id = f"created-{self._next_id}"
        self._next_id += 1
        self._playlists.append((name, playlist_id))
        self.create_calls.append(
            {"id": playlist_id, "name": name, "public": public}
        )
        return {"id": playlist_id, "name": name, "public": public}

    def playlist_add_items(
        self,
        playlist_id: str,
        items: list[str],
        position: int | None = None,
    ) -> dict[str, str]:
        self.add_calls.append((playlist_id, list(items)))
        return {"snapshot_id": "snapshot"}

    def current_user_saved_tracks_add(self, tracks: list[str]) -> None:
        self.like_calls.append(list(tracks))


def test_festive_run_backs_up_liked_songs_then_likes_christmas_playlist() -> None:
    """Dry run plans; a real run backs up and likes; a re-run reuses the backup."""
    from festive_playlists.festive import run

    sp = FakeSpotify(liked_ids=LIKED_IDS, christmas_ids=CHRISTMAS_IDS)

    plan = run(sp, TODAY, dry_run=True)

    assert plan.backup_name == BACKUP_NAME
    assert sorted(plan.track_ids) == DISTINCT_CHRISTMAS_IDS
    assert sp.create_calls == []
    assert sp.add_calls == []
    assert sp.like_calls == []

    run(sp, TODAY)

    assert [call["name"] for call in sp.create_calls] == [BACKUP_NAME]
    assert sp.create_calls[0]["public"] is False
    backup_id = sp.create_calls[0]["id"]

    assert [len(items) for _, items in sp.add_calls] == [100, 100, 50]
    assert [playlist_id for playlist_id, _ in sp.add_calls] == [backup_id] * 3
    copied = [track_id for _, items in sp.add_calls for track_id in items]
    assert sorted(copied) == LIKED_IDS

    assert [len(tracks) for tracks in sp.like_calls] == [50, 50, 20]
    liked = [track_id for tracks in sp.like_calls for track_id in tracks]
    assert sorted(liked) == DISTINCT_CHRISTMAS_IDS

    run(sp, TODAY)

    assert len(sp.create_calls) == 1, "re-running must reuse today's backup"
    assert {playlist_id for playlist_id, _ in sp.add_calls} == {backup_id}


def test_track_ids_reads_item_key_and_legacy_track_key() -> None:
    """The February 2026 rename moved ids to ``item``; ``track`` still works."""
    from festive_playlists.festive import _track_ids

    current = {
        "items": [{"item": {"id": "new-1"}}, {"item": {"id": "new-2"}}],
        "next": None,
    }
    legacy = {
        "items": [{"track": {"id": "old-1"}}, {"track": {"id": "old-2"}}],
        "next": None,
    }

    assert _track_ids(lambda **_: current, 50) == ["new-1", "new-2"]
    assert _track_ids(lambda **_: legacy, 50) == ["old-1", "old-2"]


def test_track_ids_fails_loudly_when_items_have_no_tracks() -> None:
    """A page of items with no track objects must not look like an empty list."""
    from festive_playlists.festive import _track_ids

    page = {"items": [{"name": "no track here"}], "next": None}

    with pytest.raises(ValueError, match="item"):
        _track_ids(lambda **_: page, 50)


def test_track_ids_fails_when_playlist_contents_are_unavailable() -> None:
    """Followed (non-owned) playlists come back without an ``items`` list."""
    from festive_playlists.festive import _track_ids

    page = {"total": 42, "next": None}

    with pytest.raises(ValueError, match="own or collaborate"):
        _track_ids(lambda **_: page, 50)
