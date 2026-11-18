# festive_playlists

A GitHub Actions app that automates a Spotify Christmas routine.

- **Festive run** backs up Liked Songs to a private
  `Favourites Backup YYYY-MM-DD` playlist, then likes every track in the
  `Christmas` playlist.
- **De-festive run** unlikes every track currently in the `Christmas`
  playlist. It deliberately does not restore the backup; see
  [ADR-0001](docs/adr/0001-de-festive-does-not-restore-liked-songs.md).

Both runs are manual `workflow_dispatch` pipelines. The domain model is in
[GLOSSARY.md](GLOSSARY.md).

## Secrets

Set these as repository Actions secrets (Settings → Secrets and variables →
Actions):

| Secret | Purpose |
| --- | --- |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret |
| `SPOTIFY_REFRESH_TOKEN` | Long-lived refresh token for your account |
| `SPOTIFY_CHRISTMAS_PLAYLIST_ID` | Optional; needed for 2+ `Christmas` playlists. |

The app refreshes an access token at runtime. No browser or redirect is
needed in CI. The token is never logged.

## Getting a refresh token

The easiest path is the setup wizard. Run it from the repo root on your own
machine:

```sh
./scripts/setup_spotify.sh
```

It opens the Spotify dashboard, captures your client ID and secret, runs the
authorization flow, and stores all three secrets in GitHub Actions.

To do it by hand:

1. Create a Spotify app in the
   [developer dashboard](https://developer.spotify.com/dashboard).
2. Add `http://127.0.0.1:8080/callback` as a redirect URI.
3. Run the helper on your machine:

   ```sh
   SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... \
     python3 scripts/get_refresh_token.py --output /tmp/refresh_token
   ```

4. Store the token as the `SPOTIFY_REFRESH_TOKEN` secret. The helper opens the
   consent page and catches the callback; the token is never printed when you
   use `--output`.

The refresh token stays valid while the app is used. Re-run the flow if it is
revoked.

### From your phone

A browser callback page is published at:

```text
https://willthong.github.io/festive_playlists/oauth.html
```

1. Add that exact URL as a Redirect URI in your Spotify app settings.
2. Open it on your phone and paste your Client ID.
3. Approve the Spotify consent screen.
4. Copy the refresh token shown on the page.
5. In GitHub, go to Settings → Secrets and variables → Actions and set
   `SPOTIFY_REFRESH_TOKEN` to that value.

The page uses PKCE and does not need your Client secret. It shows the token
once and does not store it.

## Running

Open the Actions tab and select **Festive run** or **De-festive run**, then
choose **Run workflow**. Tick **Preview without changing Spotify** to run in
dry-run mode. A dry run prints the backup name and the tracks that would be
liked or unliked without mutating anything.

The workflows fail fast when a required secret is missing. They run only on
demand; there is no schedule.

## Local development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ty check
```

## Behaviour and edge cases

- The Christmas playlist is matched by exact, case-insensitive name. Zero
  matches fail the run; one match is used; two or more require
  `SPOTIFY_CHRISTMAS_PLAYLIST_ID`. Spotify only returns playlist contents for
  playlists you own or collaborate on, so a followed playlist fails the run.
- The backup name uses the runner's local date. Re-running on the same day
  reuses the existing backup.
- The de-festive run warns when it removes a pre-existing like: a track that
  is in both the Christmas playlist and the most recent Favourites Backup.
  It also warns when no backup can be found to cross-check against.
