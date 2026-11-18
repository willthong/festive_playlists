# festive_playlists

A GitHub Actions app that automates a Spotify Christmas routine.

- **Festive run** — backs up Liked Songs to `Favourites Backup <yyyy-mm-dd>`,
  then likes every track in the `Christmas` playlist.
- **De-festive run** — unlikes every track currently in the `Christmas`
  playlist. It does not restore the backup (see
  `docs/adr/0001-de-festive-does-not-restore-liked-songs.md`).

Both are manual `workflow_dispatch` pipelines. See `GLOSSARY.md` for the
domain model.
