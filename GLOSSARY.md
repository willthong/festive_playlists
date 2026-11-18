# Festive Playlists

Automates the annual Spotify Christmas routine in GitHub Actions: backing up
Liked Songs and liking/unliking the Christmas playlist.

## Language

**Festive run**:
The manually triggered run that creates the Favourites Backup and then likes
every track in the Christmas Playlist.
_Avoid_: backup-and-like, decorate

**De-festive run**:
The manually triggered run that unlikes every track in the Christmas Playlist.
It does not restore the Favourites Backup (see ADR-0001).
_Avoid_: restore, cleanup

**Christmas Playlist**:
The Spotify playlist named `Christmas` that the two runs like and unlike. If
more than one playlist shares that name, the `SPOTIFY_CHRISTMAS_PLAYLIST_ID`
secret disambiguates.
_Avoid_: festive playlist, holiday playlist

**Favourites Backup**:
A private Spotify playlist, named `Favourites Backup <yyyy-mm-dd>`, that
copies Liked Songs at the moment a festive run starts. It is a manual safety
net; only the de-festive run reads it back, and only to flag pre-existing
likes.
_Avoid_: snapshot, restore point

**Liked Songs**:
A user's Spotify "Liked Songs" collection — the thing this app backs up and
modifies.

**Pre-existing like**:
A track liked before the festive run that is also in the Christmas Playlist,
and therefore also in the Favourites Backup. The de-festive run unlikes it and
flags it as unexpected.
_Avoid_: old like, accidental unlike
