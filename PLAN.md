# Mnémographe publishing pipeline: work plan

## Resume here

Claude wrote this section on 2026-11-22, while you were away.

### State

The code of every step is written, reviewed by the reviewer and security agents, fixed, and tested. Tests used scratch folders, a scratch git remote, fake Mastodon and Instagram servers, a fake `ntfy-publish`, and the molecule VMs.

Claude did not do these things:

- push or merge anything
- post to Mastodon or Instagram
- run a playbook on ws or `pi`
- register the deploy key on GitHub
- touch the real `minbox` or `Mnémographe` folders.

Claude ran only read-only checks on the real `pi`. Its timezone is America/Toronto, it reaches `https://charlesfleche.net` itself (HTTP 200), and it runs systemd 257.

The history has one commit per major step, so you can read it in order with `git log -p --reverse`. A backup branch `mnemographe-pipeline-before-reorg` keeps the history from before the reorganization, in both repositories. Delete it when you no longer need it.

charlesfleche.net, `git log --oneline --reverse master..mnemographe-pipeline`:

1. `Add the work plan of the mnémographe pipeline`: this file.
2. `Rename poster.py to mnemographe.py, poster.yml to mnemographe.yml`: a pure rename, so `git log --follow` reaches `poster.py`.
3. `Ingest new mnémographes from the Syncthing inbox`: step 1.
4. `Mirror the mnémographe gallery to the phone`: step 2.
5. `Add the mnémographe tag editor`: step 3.
6. `Post the mnémographes to Mastodon, and list the publish queue`: step 4a.
7. `Post the mnémographes to Instagram`: step 4b.
8. `Document the mnémographe pipeline`: step 5.

si, `git log --oneline --reverse main..mnemographe-pipeline`:

1. `Step 1: notify failed units with ntfy, and ingest the mnémographe inbox on ws`
2. `Step 2: mirror the mnémographe gallery to the phone after each ingest`
3. `Step 3: install mnemographe-tag, the mnémographe tag editor, on ws`
4. `Step 4c: post the mnémographe photos from pi on schedule`
5. `Step 5: document the mnémographe roles in the README`

### Step 4c is finished

On 2026-11-23, Claude rotated the deploy key and folded that change into the step 4c commit of si. Then Claude rebased the si branch on the new `main`, which has the radio and kiosk molecule fixes. Molecule passes: converge, a second converge with `changed=0` on both VMs, and verify with 0 failures.

### Your actions, in order

1. Read the commits step by step, and answer the questions below.
2. Merge `mnemographe-pipeline` into `master` in charlesfleche.net, and push. Do this before any converge, because ws and `pi` both run the code of `master`.
3. Merge `mnemographe-pipeline` into `main` in si.
4. Converge ws, with a check first:

   ```
   uv run ansible-playbook playbook.yml --limit ws --tags ntfy,mnemographe_ingest --check --diff -K
   uv run ansible-playbook playbook.yml --limit ws --tags ntfy,mnemographe_ingest -K
   ```

   The converge starts `mnemographe-watch.service`. If `minbox` holds photos, it ingests them and publishes the blog at once.
5. Log out and log in again on ws (or reboot), so your user session gets the `ntfy` group. Then check `systemctl --user status mnemographe-watch`.
6. Put one new square photo in `minbox` from the phone. Expect a notification, a commit on GitHub, the photo on the blog, and the photo in the phone's `Mnémographe` folder.
7. Run `mnemographe-tag` and tag some photos. Mastodon has no tagged photo left today: all 144 tagged photos are already posted there.
8. Mastodon from ws, once. In `~/src/charlesfleche.net-mnemograph-ingest`, run `bin/mnemographe.py post mastodon --dry-run`, then the same command without `--dry-run`, with `POSTER_MASTODON_API_TOKEN` set.
9. Set up Instagram:
    1. Switch charlesfleche_ to a Creator account.
    2. Create a Meta app with the "Instagram API with Instagram Login" product.
    3. Get a long-lived token with `instagram_business_basic` and `instagram_business_content_publish`.
10. Instagram from ws, once: `post instagram --dry-run`, then a real post, with `POSTER_INSTAGRAM_API_TOKEN` set. Two points of the API are not confirmed, but a wrong guess fails before any post:
    - the shape of the `/me` response (the code accepts both shapes that Meta's docs show)
    - `caption` on a single image.
11. Register the deploy key of `pi`, with write access, on charlesfleche.net only. Its public key is `mnemographe_deploy_key_pub` in si's `host_vars/pi/vars.yml`:

    ```
    gh repo deploy-key add <file with the public key> -R charlesfleche/charlesfleche.net --allow-write --title "pi mnemographe"
    ```

12. Add the two tokens to the vault:

    ```
    uv run ansible-vault edit host_vars/pi/vault_mnemographe.yml
    # vault_mnemographe_mastodon_token: ...
    # vault_mnemographe_instagram_token: ...
    ```

13. Converge `pi`, with a check first: `--limit pi --tags ntfy,mnemographe --check --diff -K`, then without `--check`.
14. On `pi`, run `sudo systemctl start mnemographe-post@mastodon` once. Check the commit on GitHub, then run `ssh pi mnemographe-schedule`.
15. Once `pi` posts, never run a real `post` from ws: the lock only covers one clone, so both can post the same photo.
16. When everything works, tell Claude to do these last items:
    - remove `bin/instapublish.py` and `instagrapi`
    - delete `origin/publish-mnemograph`
    - remove this file.

### Questions for you

1. Code that `pi` runs. Recommended: yes.
   - Today, anyone who can push to `master` runs code on `pi` and on ws as `charles`. On `pi`, that code can read the tokens and the deploy key.
   - The fix is to run a pinned copy of `mnemographe.py` on `pi`, outside the clone. Ansible installs it, owned by root, from a pinned commit. Then a push to `master` can no longer run code on `pi`.
   - The cost: every update of the script needs a converge.
2. Signed commits. Recommended: yes, as a second layer.
   - You sign your commits with your ssh key (ssh commit signing on ws and lp, set by the si `git` role).
   - ws then refuses any pulled commit that is not signed, unless it only touches post json files.
   - A GitHub ruleset on `master` also blocks force-push and deletion.
3. Lock the dependencies of the script with `uv lock --script`, so a malicious PyPI release cannot run with the tokens. Recommended: yes. Cost: one lock file, which you update by hand.
4. Seven originals are over Instagram's 8 MB limit. The Instagram queue stops on the first one, in about 40 days:
   - `20260805-080140.jpg` (11.2 MB), `20260805-080844.jpg` (11.4 MB)
   - `20260806-090000.jpg` (10.4 MB), `20260806-100000.jpg` (9.6 MB), `20260806-130000.jpg` (8.2 MB), `20260806-140000.jpg` (9.2 MB), `20260806-150000.jpg` (8.9 MB)

   Options:
   - replace these originals with smaller files
   - send the largest JPEG of the site build instead (960 px)
   - add a resized copy for Instagram only.

   Recommended: replace the 7 originals, and make ingest refuse files over 8 MB.
5. The phone gallery as its own Syncthing folder, "Send Only" on ws and "Receive Only" on the phone. Then the phone can never change it, for example by replacing it with a symbolic link. The code already refuses that case and pins the folder. This needs a change on the phone.
6. Answered: `pi` commits with your usual identity, Charles Flèche `<charles.fleche@free.fr>`.
7. Empty queues send warnings: Mastodon once a day, Instagram 3 times a day, until you tag photos. Is that OK, or do you want one warning a day at most?
8. Clearing the alt text of a photo that also has an alt text in another language removes only the default one. The site then shows the other language. No sidecar has a second language today.

### Decisions Claude took while you were away

- Rename date priority: DateTimeOriginal, then CreateDate, then GPSDateTime. That is what `rename.sh` really did. The plan text had the reverse order.
- Ingest refuses these files, with one notification that lists them all, and nothing moves:
  - hidden files (`.trashed-*` from the Android trash, `.syncthing.*.tmp`)
  - symbolic links, directories and other non-regular files
  - non-JPEG files, and photos larger than 8000 px
  - photos that are not square within 1%, or that have no EXIF date
  - name collisions.
- exiftool does all the checks, and Pillow is gone. A JPEG cut off in its pixel data is not detected. That is acceptable, because Syncthing only moves a file into place once it is complete.
- A failure in `watch` crashes it. systemd restarts it up to 5 times, then `OnFailure=` sends one notification. A refused inbox notifies once and keeps watching.
- Every writing command first runs `git pull --rebase` and pushes pending commits. It refuses any uncommitted file in the gallery, and holds a `flock` in `.git/`.
- A post writes `<stem>.<network>.pending` before the call that makes it public. If a marker is left, the next run stops and names it: check the network, write the json by hand if the photo is posted, and delete the marker in both cases.
- The Instagram token is stored in `instagram-token.json` at the root of the clone, ignored by git (your choice on 2026-11-23), mode 0600, and refreshed after 7 days, even when nothing is posted. A new environment token replaces it by itself.
- Tokens never reach child processes, and errors never print them.
- `ntfy-publish` now runs `ntfy publish --quiet`, because the server reply holds the topic and went into the journals. This also changes borgmatic, fail2ban and unattended-upgrades.
- `ntfy-failure@` sends the last 3500 bytes of the journal, through an environment variable instead of argv.
- `ansible_user` is in the `ntfy` group on every host, because `pi` needs it. The security review suggested ws only.
- GPS stays in the EXIF, as you decided. The security review flagged it again.
- The tag editor uses `git var GIT_EDITOR`. "Newest added" follows renames. Only 19 commits ever added photos, so many photos share a time.
- The mirror refuses these targets:
  - a symbolic link
  - a folder in the repository, or one that holds the repository
  - a folder with subfolders
  - a folder where more than half of the names are not in the gallery.

  rsync writes into the folder that was checked, pinned by a file descriptor.
- `pi` timers: Mastodon at 12:00 exactly. It can start a few minutes late when the 11:45 Instagram window holds the lock.

### Incidents, nothing reached the outside

- An agent's test loop almost ran `publish.sh` without an argument, which publishes to the real `pi`. The auto-mode classifier blocked it, and nothing ran.
- One `ntfy-failure` test reached the real `ntfy-publish`. It failed on the unreadable topic file, so nothing was sent.
- The first deploy key reached the molecule VM disks. It was never registered, it is shredded from the VM, and Claude rotated it on 2026-11-23.
- The molecule VMs were broken (ISOs owned by libvirt). You approved the reset.

### Known problems, not part of this work

- The molecule VMs hold the real ntfy topic, and their ntfy client sends to ntfy.sh outside verify.

## Context

Mnémographes are square photos published to the gallery page of charlesfleche.net (`content/page/2022-01-01-mnemographe`), to Mastodon (charlesfleche@mamot.fr) and, soon, to Instagram (charlesfleche_). Today every step is manual: copy the photos, rename them with `rename.sh`, commit, publish, copy the folder to the phone, tag in the Mastodon UI.

The target workflow:

1. You put photos in `~/Syncthing/3a-Pictures/minbox` on the phone.
2. You get a notification that new photos need tags, and you tag them on ws in a text editor.

The rest is automatic: ws ingests, commits, pushes, publishes the blog and updates the phone gallery. `pi` posts the tagged photos to Mastodon and Instagram on a schedule, even when ws is off.

### What exists

- `bin/poster.py` (charlesfleche.net) posts to Mastodon. The XMP sidecar `<stem>.xmp` holds the tags (`dc:subject`) and the alt text (`dc:description`). `<stem>.mastodon.json`, the API response, marks a photo as posted. `import` rebuilt that state from the Mastodon history: 144 of 325 photos are tagged and posted.
- `bin/instapublish.py` is a broken instagrapi stub. `origin/publish-mnemograph` holds an old experiment (`bin/mg.py`).
- `bin/publish.sh` builds the site and rsyncs `build/dist/` to `pi:/srv/www/charlesfleche.net/`.
- `~/Syncthing/3a-Pictures/Mnémographe` is a manual copy of the gallery folder. Only ws and the phone share `3a-Pictures`. `minbox` is a subfolder of it, not a Syncthing folder of its own.
- si: the `ntfy` role installs `ntfy-publish` on every host (`common` play). Its `/etc/ntfy/topic.env` is root-only (`u=r`), so `charles` cannot notify yet. The Syncthing API key is in the vault (`syncthing_gui_apikey`) and in ws's `~/.config/syncthing/config.xml`.
- ssh as `charles`: on ws, `id_ed25519` has no passphrase and reaches `pi` and GitHub. On `pi`, `charles` has no key and no `github.com` host key, and git and uv are not installed.

### Decisions

| Topic | Decision |
|---|---|
| Publish order | Oldest file name first, among the tagged photos that the network has not got yet. Untagged photos are skipped, never block. |
| Instagram | Official Instagram API with Instagram Login (Creator or Business account). Instagram fetches the photo from its charlesfleche.net URL. |
| Ingest host | ws. A user service listens to the Syncthing events API and ingests when `3a-Pictures` is idle after a change in `minbox/`. |
| EXIF | Kept as it is, GPS included. |
| Square rule | Ingest rejects a photo whose sides differ by more than 1%. All 325 current photos pass (worst 0.93%), and Instagram accepts them as they are. |
| Post state | `pi` commits `<stem>.<network>.json` and pushes to GitHub. The repo is the only source of truth. No GitHub Action. |
| Blog deploy | The ingest runs `publish.sh` on ws. `pi` never builds nor deploys the site. |
| User | Everything runs as `charles`, on ws and on `pi`. No service user. ws uses `charles`'s existing keys. `pi` gets a new deploy key for charlesfleche.net only. |
| ws working copy | A dedicated clone, `~/src/charlesfleche.net-mnemograph-ingest`, always on master. Ingest and tag run there. Your `~/src/charlesfleche.net` is never touched. |
| Phone gallery | The ingest itself mirrors the whole gallery folder with `rsync --delete`. |
| Tag editor | Every photo, newest added on top, with its posted networks shown. |
| Schedule | Defined only in the si playbook (timer vars). Mastodon at 12:00 exactly. Instagram around 7:00, 12:00 and 17:00, each in a 30 minute random window. `mnemographe.py` knows nothing about time. |
| Cleanup | `instapublish.py` and `instagrapi` go away only when the whole pipeline works (end of step 4c). |

### Proposed defaults (correct them at review)

- One tool: `git mv bin/poster.py bin/mnemographe.py`, with subcommands `ingest`, `tag`, `post` and `queue`. `poster.yml` becomes `mnemographe.yml`.
- `import` and the `imagehash` dependency go away: their one-time job is done. `tag IMAGE TAGS` and `list` go away too, replaced by the editor and `queue`.
- `queue NETWORK` prints the next tagged photos of a network in publish order, without dates.
- Ingest uses `exiftool` with the `rename.sh` rule (`GPSDateTime`, then `CreateDate`, then `DateTimeOriginal`, as `%Y%m%d-%H%M%S.<lowercase ext>`). `rename.sh` leaves the gallery.
- A photo without an EXIF date, a name collision, a non-JPEG file or a non-square photo stops the ingest before any file moves. The files stay in minbox, and you get a notification.
- "Newest added" is the date of the commit that added the photo (`git log --diff-filter=A`), then the file name, descending.
- The Instagram window is centered on the hour: `OnCalendar=06:45`, `11:45`, `16:45` with `RandomizedDelaySec=30min`. Missed slots are skipped (`Persistent=false`), so posts never burst after downtime.
- `mnemographe-schedule`, installed on `pi` by si, prints the next slots of each timer (`systemd-analyze calendar --iterations` on the timer's `OnCalendar`) next to `mnemographe.py queue`. From ws: `ssh pi mnemographe-schedule`.
- On `pi`, system units run as `User=charles` (no lingering needed). Both network jobs take the same `flock`, because both run at 12:00 in the same clone.
- The Instagram long-lived token (60 days) is refreshed by the publisher. The refreshed token stays in `instagram-token.json` at the root of the clone on `pi`, ignored by git. The vault holds the first token only.

### Challenges to your instructions

- The ssh key on `pi` (agreed). `charles` on `pi` gets one new key that only writes to charlesfleche.net:
  - I generate an ed25519 key on ws. Its private part goes into the si vault, so a reinstalled `pi` gets the same key back.
  - I add its public part as a deploy key of charlesfleche.net with write access (`gh repo deploy-key add --allow-write`), after your OK. It is not an account key: a leaked `pi` (it faces the internet) can push to this repository only.
  - The playbook installs it as `~charles/.ssh/github-charlesfleche.net` (`0600`). The clone uses it through its own `core.sshCommand` (`-i` that key, `IdentitiesOnly=yes`). It is not `id_ed25519`, so nothing else on `pi` uses it.
  - The playbook pins the `github.com` host keys in `known_hosts`.
  - The security agent reviews the whole setup before the first converge on `pi`.
- The Syncthing API. I agree: it is more correct than a path unit, which cannot know when a sync is finished. It costs a long-running service of a few dozen lines. These are the details that keep it simple:
  - `minbox` is not its own Syncthing folder, so the listener waits for `3a-Pictures` to become `idle` (event `StateChanged`) after an `ItemFinished` in `minbox/`. A large sync elsewhere in `3a-Pictures` delays the ingest until it ends.
  - The API key is read from Syncthing's own `config.xml`, so there is no new secret.
  - At start, the listener ingests if minbox is not empty. This catches photos that arrived while ws was off.
  - `Restart=on-failure` covers Syncthing restarts. `OnFailure=` notifies only when systemd gives up (`StartLimitBurst`), so a Syncthing restart never spams you.

## How we work

- Two worktrees, each on a branch `mnemographe-pipeline`:
  - `~/src/charlesfleche.net-mnemographe`, from `master`;
  - `~/src/si-mnemographe`, from `main`.
- This plan is committed as `PLAN.md` in the charlesfleche.net worktree and kept up to date there, with its checkboxes. It is removed in the last step. The lasting documentation goes into the READMEs.
- Each step is one gate. I do as many commits as needed during the step. When you approve the step, I squash it to one commit per repository. I merge to master or main and push only when you say so, because the automation runs from master.
- Real posts, pushes to GitHub, and playbook runs on ws or `pi` are outward-facing: I ask before each first run. Playbook runs that need sudo are yours (`! uv run ansible-playbook ... -K`).
- Development tests never touch GitHub nor the networks: ingest and tag push to a bare repo in the scratchpad, and `post` runs with `--dry-run` until you approve a real post.

### Agents

I coordinate and give each agent only the context of the step: the items, the files, the decisions above, and the two memory rules (fail loudly, no magic; tools through `uv run`).

| Agent | Type | Job |
|---|---|---|
| implementer | general-purpose, in the worktree | Writes the code of one step, runs its checks, commits. |
| reviewer | general-purpose | Reviews the step diff for bugs, simplicity, reuse, and the CLAUDE.md conventions of both repos. |
| security | general-purpose | Reviews the step diff for secrets, key scopes, file modes, systemd hardening, shell injection through file names, and the ntfy topic. |
| ansible tester | general-purpose, only for si steps | Runs `ansible-lint`, molecule converge, a second converge with `changed=0`, and verify. |

Loop for each step: implementer, then reviewer and security in parallel, then implementer fixes, then I check the result myself and show it to you.

### Notifications

Every notification goes through `ntfy-publish`.

| When | Message |
|---|---|
| Ingest done | N photos added, blog published, phone gallery updated, M photos to tag |
| A post done | network, file name, post URL |
| A network has no tagged photo left | warning: tag more photos |
| Any unit fails | error, with the end of its journal (`OnFailure=`) |

## Step 0: setup

- [x] Create both worktrees and branches.
- [x] Commit this plan as `PLAN.md` in the charlesfleche.net worktree.

## Step 1: ingest on ws

charlesfleche.net:
- [x] Rename `poster.py` to `mnemographe.py` and `poster.yml` to `mnemographe.yml`. Remove `import`, `list`, the old `tag` and `imagehash`.
- [x] `mnemographe.py ingest INBOX`:
  1. Pull master (`--ff-only`).
  2. Check every file of INBOX first: JPEG, EXIF date, square within 1%, no name collision.
  3. Rename with exiftool and move into the gallery.
  4. Commit `Add N photos to mnémographe`, rebase on the remote, and push.
  5. Run `publish.sh`.
  6. Notify.
- [x] `mnemographe.py watch INBOX`: the Syncthing listener described in the challenges. It runs `ingest` in the same process.
- [x] Remove `rename.sh` from the gallery.

si:
- [x] `ntfy`: a group `ntfy` that can read `topic.env`, with `charles` in it on ws and `pi`, and a reusable `ntfy-failure@.service` template for `OnFailure=`.
- [x] New role `mnemographe_ingest` (`wss_desktop` play):
  - installs `libimage-exiftool-perl`;
  - clones `~/src/charlesfleche.net-mnemograph-ingest` if it is missing;
  - installs and enables the user unit `mnemographe-watch.service`.

Check:
1. Ingest a few test photos from a scratch minbox into a scratch bare remote.
2. Ingest a bad photo (no EXIF date, not square) and see the failure notification.
3. Run the listener against the real Syncthing with a scratch inbox, and copy a photo to minbox from the phone.
4. With your OK, one real ingest on ws.

## Step 2: phone gallery on ws

- [x] After the push, `ingest` mirrors the gallery folder to `~/Syncthing/3a-Pictures/Mnémographe` with `rsync --delete`. The ingest notification says so.
- [x] `tag` (step 3) mirrors the same way.

Warning: a file added on the phone to `Mnémographe` is deleted at the next mirror. Only minbox takes new photos.

Check: the mirror of a test gallery to a scratch folder, then a real mirror, with your OK.

## Step 3: tag editor on ws

- [x] `mnemographe.py tag`:
  1. Pull the ingest clone.
  2. Write a temporary file and open it in `$VISUAL` or `$EDITOR`, as `git rebase -i` does.
  3. On save, write only the XMP files that changed.
  4. Commit `Tag N mnémographe photos`, push, and mirror to the phone.

  An unchanged file, an empty file or a non-zero editor exit aborts without a change.
- [x] File format. The first column shows the networks (`m` Mastodon, `i` Instagram, `-` none) and is ignored on save. A removed line leaves its photo unchanged. An unknown file name or a duplicate line stops with an error and writes nothing.

  ```
  # Tag the mnémographes, newest added first. One photo per line:
  #   <posted> <file> <tag> <tag> ... [| <alt text>]
  mi 20260807-120000.jpg Montréal Vélo | Two bicycles in the snow
  -- 20261121-153429.jpeg
  ```
- [x] A `mnemographe-tag` command on ws (installed by `mnemographe_ingest`) runs it in the ingest clone.

Check:
- A round trip on a scratch clone: no change, add tags, remove tags, alt text with `|` and `#`, bad lines.
- The XMP files still read correctly with `exiftool -XMP-dc:Subject`.
- The site build still finds the alt texts.

## Step 4a: Mastodon publisher, run from ws

- [x] `mnemographe.py post mastodon`:
  1. Pull.
  2. Take the oldest tagged photo without `<stem>.mastodon.json`.
  3. Post it, keeping the `Idempotency-Key`.
  4. Write the json, commit and push.
  5. Notify with the post URL.

  A post whose push fails stays committed in the clone, so the next run pushes it and never posts the photo again.
- [x] No tagged photo left: notify a warning and exit with success.
- [x] `mnemographe.py queue mastodon`.

Check: `--dry-run` against the real gallery. Then one real post, with your OK.

## Step 4b: Instagram publisher, run from ws

You do these by hand, with the instructions I write:
- [ ] Switch charlesfleche_ to a Creator account.
- [ ] Create a Meta app with the Instagram API product.
- [ ] Get a long-lived token with `instagram_business_basic` and `instagram_business_content_publish`.

Code:
- [x] An `Instagram` destination class, next to `Mastodon`:
  1. Create a media container with the `image_url` of the photo on charlesfleche.net, the caption (hashtags, 30 at most) and, if the API supports it, the alt text.
  2. Wait for the container to finish.
  3. Publish the container.
  4. Refresh the token when it is older than 7 days.
- [x] Before posting, a `HEAD` on the image URL: a photo not yet on the blog fails clearly.

Check: `--dry-run`, then one real post with your OK.

## Step 4c: publishing from pi

si, new role `mnemographe` (`servers` play):
- [x] git and uv on `pi`, from Debian and latest-debs.
- [ ] The charlesfleche.net deploy key on `pi`, from the vault, and the pinned `github.com` host keys (see the challenges). With your OK, I register the key on GitHub with `gh`. Done, except the GitHub registration, which waits for you (see Resume here). The key was rotated once, because the first one reached the molecule VM disks.
- [x] Clone `~charles/src/charlesfleche.net` if it is missing.
- [x] `/etc/mnemographe/env` (`root:charles`, `0440`) with the Mastodon token and the first Instagram token, from the vault. Changed after review: `root:root`, `0400`, because systemd reads it as root.
- [x] `mnemographe-post@.service`, with `User=charles`, `flock`, `OnFailure=` to ntfy, and the hardening that `uv` and `git` allow. One `mnemographe-post@<network>.timer` per network, from role vars: Mastodon `12:00`, Instagram `06:45,11:45,16:45` with `RandomizedDelaySec=30min`. Changed after review: Instagram is `*-*-* 06,11,16:45:00`, because systemd refuses `06:45,11:45,16:45`. The script takes its own `flock`, so the unit has none.
- [x] `mnemographe-schedule` in `/usr/local/bin`.
- [x] In molecule (`deployment_is_dev`): no key and no tokens. The timers exist but are disabled, and verify checks the units and modes. Changed after review: a fake key and fake tokens, and a real clone from a git bundle of the branch, so verify runs the real unit with `--dry-run`.

Check:
1. `ansible-lint`, molecule converge, a second converge with `changed=0`, and verify.
2. With your OK, converge on `pi`.
3. Run `systemctl start mnemographe-post@mastodon` once by hand, and see the commit on GitHub.
4. Run `ssh pi mnemographe-schedule`.

When the whole pipeline works:
- [ ] Remove `bin/instapublish.py` and `instagrapi` from `requirements.txt`. Not done: you asked to remove it once real posts work.

## Step 5: documentation and cleanup

- [x] charlesfleche.net `README.md`: a short Mnémographe section with the flow, the commands (`mnemographe-tag`, `ssh pi mnemographe-schedule`) and where things fail. Update `CLAUDE.md` (the `poster.py` and `instapublish.py` paragraphs).
- [x] si `README.md`: the new roles in the play table and the services diagram, and the vault variables.
- [ ] With your OK, delete the remote branch `origin/publish-mnemograph`.
- [ ] Remove `PLAN.md`.

## Verification, end to end

1. Put two new square photos in minbox on the phone.
2. Within minutes, check:
   - a notification "2 photos added, M to tag";
   - the commit on GitHub;
   - the photos on https://charlesfleche.net/mnemographe/;
   - the photos in the phone's `Mnémographe` folder.
3. Run `mnemographe-tag`, tag them, then `ssh pi mnemographe-schedule`: they are in the queues.
4. Switch ws off. At the next slots, the posts appear on Mastodon and Instagram, with notifications, and `pi`'s json commits are on GitHub.
5. Break something on purpose (a non-square photo in minbox, then a wrong token on `pi`). Each time, you get an error notification.
