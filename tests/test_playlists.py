"""Christmas Playlist resolution behind ``festive_playlists.playlists``."""

import logging

import pytest


class FakeSpotify:
    """Minimal paginating stand-in for ``spotipy.Spotify`` playlists."""

    def __init__(
        self,
        playlists: list[tuple[str, str]],
        *,
        page_size: int = 2,
    ) -> None:
        self._playlists = playlists
        self._page_size = page_size

    def current_user_playlists(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        page = self._playlists[offset : offset + self._page_size]
        next_offset = offset + self._page_size
        has_next = next_offset < len(self._playlists)
        return {
            "items": [{"id": playlist_id, "name": name} for name, playlist_id in page],
            "next": (
                f"https://api.spotify.com/v1/me/playlists?offset={next_offset}"
                if has_next
                else None
            ),
        }


@pytest.mark.parametrize(
    (
        "playlists",
        "christmas_id",
        "expected_id",
        "error_match",
        "warning_match",
    ),
    [
        pytest.param(
            [
                ("Road Trip", "id-trip"),
                ("Christmas Eve", "id-eve"),
                ("Christmas Party", "id-party"),
                ("Christmas Lights", "id-lights"),
            ],
            None,
            None,
            "Christmas",
            None,
            id="no-playlist-named-christmas",
        ),
        pytest.param(
            [
                ("Road Trip", "id-trip"),
                ("Christmas Eve", "id-eve"),
                ("christmas", "id-christmas"),
            ],
            None,
            "id-christmas",
            None,
            None,
            id="one-playlist-any-case",
        ),
        pytest.param(
            [
                ("Road Trip", "id-trip"),
                ("Christmas Eve", "id-eve"),
                ("Christmas", "id-capital"),
                ("CHRISTMAS", "id-upper"),
            ],
            None,
            None,
            "Christmas",
            None,
            id="ambiguous-without-explicit-id",
        ),
        pytest.param(
            [
                ("Road Trip", "id-trip"),
                ("Christmas Eve", "id-eve"),
                ("Christmas", "id-capital"),
                ("christmas", "id-lower"),
            ],
            "id-lower",
            "id-lower",
            None,
            "Christmas",
            id="ambiguous-with-explicit-id",
        ),
    ],
)
def test_resolve_christmas_playlist(
    playlists: list[tuple[str, str]],
    christmas_id: str | None,
    expected_id: str | None,
    error_match: str | None,
    warning_match: str | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from festive_playlists.playlists import resolve_christmas_playlist

    fake = FakeSpotify(playlists)

    with caplog.at_level(logging.WARNING):
        if error_match is not None:
            with pytest.raises(ValueError, match=error_match):
                resolve_christmas_playlist(fake, christmas_id=christmas_id)
        else:
            resolved = resolve_christmas_playlist(fake, christmas_id=christmas_id)
            assert resolved == expected_id

    if warning_match is not None:
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, caplog.text
        assert warning_match.lower() in warnings[0].getMessage().lower()
