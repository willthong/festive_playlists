"""Favourites Backup slice behind ``festive_playlists.playlists``."""

from datetime import date

USER_ID = "user-1"


class FakeSpotify:
    """Small stand-in for the ``spotipy.Spotify`` playlist operations we use."""

    def __init__(self, playlists: list[tuple[str, str]]) -> None:
        self._playlists = list(playlists)
        self._public = {playlist_id: True for _, playlist_id in playlists}
        self.create_calls: list[dict[str, object]] = []
        self._next_id = 1

    def me(self) -> dict[str, str]:
        return {"id": USER_ID}

    current_user = me

    def current_user_playlists(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        page = self._playlists[offset : offset + limit]
        next_offset = offset + limit
        has_next = next_offset < len(self._playlists)
        return {
            "items": [{"id": playlist_id, "name": name} for name, playlist_id in page],
            "next": (
                f"https://api.spotify.com/v1/me/playlists?offset={next_offset}"
                if has_next
                else None
            ),
        }

    def user_playlist_create(
        self,
        user: str,
        name: str,
        public: bool = True,
        description: str = "",
    ) -> dict[str, object]:
        assert user == USER_ID, user
        playlist_id = f"created-{self._next_id}"
        self._next_id += 1
        self._playlists.append((name, playlist_id))
        self._public[playlist_id] = public
        self.create_calls.append({"name": name, "public": public})
        return {"id": playlist_id, "name": name, "public": public}

    def user_playlist(
        self,
        playlist_id: str,
        fields: str | None = None,
    ) -> dict[str, object]:
        for name, known_id in self._playlists:
            if known_id == playlist_id:
                return {
                    "id": known_id,
                    "name": name,
                    "public": self._public.get(known_id, True),
                }
        raise KeyError(playlist_id)

    playlist = user_playlist


def test_favourites_backup_slice() -> None:
    """Reuse today's backup, create it when missing, and find the latest."""
    from festive_playlists.playlists import find_or_create_backup, most_recent_backup

    today = date(2025, 12, 24)
    sp = FakeSpotify(
        [
            ("Christmas", "id-christmas"),
            ("Road Trip", "id-trip"),
            ("Favourites Backup 2024-12-24", "id-last-year"),
        ]
    )

    created_id = find_or_create_backup(sp, today)

    assert sp.create_calls == [
        {"name": "Favourites Backup 2025-12-24", "public": False}
    ]
    assert sp.user_playlist(created_id)["name"] == "Favourites Backup 2025-12-24"
    assert sp.user_playlist(created_id)["public"] is False

    assert find_or_create_backup(sp, today) == created_id
    assert len(sp.create_calls) == 1, "today's existing backup must be reused"

    assert most_recent_backup(sp) == created_id

    no_backups = FakeSpotify([("Christmas", "id-christmas"), ("Road Trip", "id-trip")])
    assert most_recent_backup(no_backups) is None
