# My blog

```sh
python bin/mkbuild.py
```

## Mnémographe

The mnémographes are the square photos of `content/page/2022-01-01-mnemographe`. They also go to Mastodon and Instagram.

1. On the phone, put new photos in `3a-Pictures/minbox`. Syncthing copies them to ws.
2. On ws, `mnemographe-watch.service` ingests them. It renames them after their date, commits and pushes them, publishes the blog, and mirrors the gallery to the phone's `3a-Pictures/Mnémographe`.
3. A notification says how many photos have no tags. Run `mnemographe-tag` on ws to tag them.
4. pi posts the tagged photos on its timers: Mastodon at 12:00, Instagram around 7:00, 12:00 and 17:00. It pushes a json for each post and sends a notification.

Untagged photos are skipped. Each network gets the oldest tagged photo it does not have yet.

Once pi posts, never run a real `post` from ws. The lock only covers one clone, so both could post the same photo.

### Commands

```sh
mnemographe-tag                                  # ws: edit the tags and alt texts
ssh pi mnemographe-schedule                      # the next posts of each network
bin/mnemographe.py queue mastodon                # the photos a network gets next (git pull first)
bin/mnemographe.py post instagram --dry-run      # what the next post would be
journalctl --user -u mnemographe-watch           # ws: the ingest
ssh pi journalctl -u mnemographe-post@instagram  # pi: the posts of a network
```

`queue` and `post --dry-run` do not pull. On ws, run `git pull` first, or use `ssh pi mnemographe-schedule`.

### When something fails

- **The inbox is refused.** The notification lists each file and its problem: not a JPEG, not square, no EXIF date, or a name already taken. Nothing moved. Fix or remove the files on the phone. The next sync starts a new ingest.
- **A `.pending` marker stops the posts.** A post crashed after the network got it, or just before. The error names the photo, its json and its marker. Check the network for the photo. If it is posted, write `<stem>.<network>.json` by hand and commit it. In both cases, delete the marker.
- **A file of the gallery is not committed.** The error names it. Commit it or remove it by hand, then push.
- **Instagram asks to confirm a login.** The post fails and notifies. Approve the login in the Instagram app, then start `mnemographe-post@instagram` again on pi. Instagram uses its private API, through instagrapi: Instagram can refuse or lock a login from a server.
- **The Instagram password changed.** Put the new password in the si vault and converge pi. If the session still fails, delete `instagram-session.json` at the root of pi's clone.
- **A unit gives up.** systemd sends a notification with the end of its journal. Read the full journal with the commands above.

### Where things are

- `<stem>.xmp` holds the tags and the alt text of a photo.
- `<stem>.<network>.json` marks a photo as posted to that network.
- On ws, the ingest and the tag editor work in their own clone, `~/src/charlesfleche.net-mnemograph-ingest`.
- On pi, the posts work in `~/src/charlesfleche.net`.
- The si repository installs the rest: roles `ntfy`, `mnemographe_ingest` and `mnemographe`.
