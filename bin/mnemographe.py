#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["instagrapi", "requests", "pyyaml"]
# ///
"""mnemographe.py — ingest new photos into the mnémographe gallery, tag and post them.

The gallery is the folder named by `images` in mnemographe.yml, at the root of
the git repository holding this script: content/page/2022-01-01-mnemographe.

ingest, tag and a real post start with git pull --rebase and git push, so a
commit a previous run could not push goes out. They fail first on any
uncommitted file of the gallery. After their own commit, they pull --rebase
and push again. They hold a lock in the git directory: ingest and post for
their whole run, tag before and after its editor, not while it is open. watch
runs ingest. queue and post --dry-run run no git at all.

ingest INBOX --mirror DIR checks every file of INBOX first, and moves nothing
if one is not a square JPEG with an EXIF date, or would collide with another
photo: it notifies the problems. Otherwise it renames the photos after their
date, %Y%m%d-%H%M%S.<lowercase extension> (DateTimeOriginal, else CreateDate,
else GPSDateTime), moves them into the gallery, commits, pushes, publishes the
blog with bin/publish.sh, mirrors the gallery to DIR, and notifies.

DIR, an existing directory outside the repository that mostly holds gallery
files, becomes a copy of the gallery with rsync --delete.

watch INBOX --mirror DIR listens to the local Syncthing REST API, and runs
ingest each time the Syncthing folder holding INBOX is idle after a change in
INBOX. INBOX is a subfolder of a Syncthing folder. With --autotag-unit UNIT,
ingest then starts the systemd user unit UNIT, without waiting for it.

autotag --mirror DIR has Claude tag the photos missing tags or an alt text,
headless (claude --print), with the mnemographe-tag skill as its system
prompt. It measures what Claude cannot see (camera, GPS position, color or
black and white), puts the photos on contact sheets, and gives Claude only the
Read tool, in a directory holding the sheets alone: no shell, no other file.
It fills only the missing fields, with the checks of the tag editor, then
commits, pushes, mirrors, publishes the blog, and notifies the tags and alt
texts with Claude's guesses. It fails, writing nothing, on any answer it
refuses. It goes on with the photos ingested meanwhile.

tag --mirror DIR opens every photo, newest added first, with its tags and alt
text, in git's editor. On save, it writes the XMP sidecars <stem>.xmp that
changed (dc:subject and dc:description), commits, pushes and mirrors. The
header of the edited file explains its format.

post NETWORK posts the tagged photo with the oldest file name not posted to
NETWORK yet, skipping untagged ones, then commits and pushes
<stem>.<network>.json, the API responses, which marks it as posted, and
notifies the post URL. Without a tagged photo left, it notifies a warning.
--dry-run only prints what it would post: no git, no network, no token.

Right before the call that makes a post public, post writes
<stem>.<network>.pending, and removes it once the json is written. A marker
left by a crash stops later posts to that network: check the network, write
the json by hand if the photo is posted, and delete the marker. On Mastodon,
the same Idempotency-Key for a given photo also makes a retry within an hour
return the first post.

queue NETWORK lists the tagged photos NETWORK will get, in publish order.

Networks are configured in mnemographe.yml. Secrets come from the
environment only, and never reach child processes: Mastodon reads its access
token from POSTER_MASTODON_API_TOKEN, Instagram its password from
POSTER_INSTAGRAM_PASSWORD. Instagram keeps its session in
instagram-session.json, at the root of the repository and ignored by git: see
the Instagram class.

Usage:

    bin/mnemographe.py ingest ~/Syncthing/3a-Pictures/minbox --mirror ~/Syncthing/3a-Pictures/Mnémographe
    bin/mnemographe.py watch ~/Syncthing/3a-Pictures/minbox --mirror ~/Syncthing/3a-Pictures/Mnémographe
    bin/mnemographe.py tag --mirror ~/Syncthing/3a-Pictures/Mnémographe
    bin/mnemographe.py autotag --mirror ~/Syncthing/3a-Pictures/Mnémographe
    bin/mnemographe.py post mastodon --dry-run
    bin/mnemographe.py queue instagram
"""

import argparse
import contextlib
import dataclasses
import fcntl
import json
import math
import mimetypes
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import xml.etree.ElementTree as ET

import instagrapi
import instagrapi.exceptions
import requests
import yaml

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "mnemographe.yml"
_IMAGE_SUFFIXES = (".jpg", ".jpeg")

# Ingest renames photos after the last of these tags they have, as
# exiftool -filename<GPSDateTime -filename<CreateDate -filename<DateTimeOriginal
_RENAME_DATE_TAGS = ("GPSDateTime", "CreateDate", "DateTimeOriginal")
_RENAME_DATE_FORMAT = "%Y%m%d-%H%M%S"
_RENAME_DATE_RE = re.compile(r"\d{8}-\d{6}")
# The sides of a square photo differ by 1% at most
_SQUARE_TOLERANCE = 0.01
# Larger than any photo of the gallery (6144 px)
_MAX_SIDE = 8000

# autotag: the skill that tells Claude how to tag, and how Claude gets the photos
_SKILL_PATH = _REPO_ROOT / ".claude" / "skills" / "mnemographe-tag" / "SKILL.md"
_AUTOTAG_SHEET_SIZE = 16
# Above this mean HSL saturation, a photo is in color
_AUTOTAG_COLOR_SATURATION = 0.05
_AUTOTAG_TIMEOUT = 30 * 60
_AUTOTAG_SCHEMA = {
    "type": "object",
    "properties": {
        "photos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "the file name, as given"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "base tags first"},
                    "alt": {"type": "string", "description": "English. / French."},
                    "guesses": {"type": "string", "description": "what you are not sure of, empty if nothing"},
                },
                "required": ["file", "tags", "alt", "guesses"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["photos"],
    "additionalProperties": False,
}

_SYNCTHING_CONFIG_PATH = pathlib.Path.home() / ".config" / "syncthing" / "config.xml"
_SYNCTHING_URL = "http://127.0.0.1:8384"
_SYNCTHING_EVENTS = "ItemFinished,StateChanged"

_XMP_NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
}
for _prefix, _uri in _XMP_NS.items():
    ET.register_namespace(_prefix, _uri)

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XMP_TEMPLATE = """<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="mnemographe.py">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"/>
 </rdf:RDF>
</x:xmpmeta>"""
_XPACKET_BEGIN = '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
_XPACKET_END = '\n<?xpacket end="w"?>\n'

_NON_WORD_RE = re.compile(r"\W")
_TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")
# Characters XML 1.0 does not allow
_NOT_XML_RE = re.compile("[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")

# The tag editor's first column: a letter per network the photo is posted to
_POSTED_COLUMN = {"mastodon": "m", "instagram": "i"}
_POSTED_RE = re.compile("".join(f"[{letter}-]" for letter in _POSTED_COLUMN.values()))
_TAGS_FILE_NAME = "MNEMOGRAPHE_TAGS"
_TAGS_FILE_HEADER = """\
# Tag the mnémographes, newest added first. One photo per line:
#   <posted> <file> <tag> <tag> ... [| <alt text>]
# <posted> shows the networks the photo is posted to: m Mastodon, i Instagram,
# - not yet. It is ignored on save.
# Tags are separated by spaces, without #, and hold letters, digits and _ only.
# The alt text is everything after the first |. No |: no alt text.
# A removed line leaves its photo unchanged. Lines starting with # are ignored.
# An editor exiting with an error, or no photo line at all, changes nothing.
"""


class MnemographeError(Exception):
    """An error worth exiting on, printed without a traceback."""


def _q(name: str) -> str:
    """Qualify a prefixed XMP tag name, e.g. dc:subject."""
    prefix, _, local = name.partition(":")
    return f"{{{_XMP_NS[prefix]}}}{local}"


class Xmp:
    """An XMP sidecar, read and written with the standard library only."""

    def __init__(self, path: pathlib.Path, root: ET.Element) -> None:
        self.path = path
        self.root = root

    @classmethod
    def load(cls, path: pathlib.Path) -> "Xmp":
        if path.exists():
            # The file's own prefixes, e.g. darktable:, survive a save
            for _, (prefix, uri) in ET.iterparse(path, events=("start-ns",)):
                if prefix:
                    ET.register_namespace(prefix, uri)
            root = ET.parse(path).getroot()
        else:
            root = ET.fromstring(_XMP_TEMPLATE)
        return cls(path, root)

    @classmethod
    def for_image(cls, image: pathlib.Path) -> "Xmp":
        return cls.load(image.with_suffix(".xmp"))

    def _descriptions(self) -> list[ET.Element]:
        return list(self.root.iter(_q("rdf:Description")))

    def _find(self, name: str) -> ET.Element | None:
        return next(iter(self.root.iter(_q(name))), None)

    def _first_description(self) -> ET.Element:
        """The first rdf:Description, created if there is none."""
        description = self._find("rdf:Description")
        if description is None:
            rdf = self.root.find(_q("rdf:RDF"))
            if rdf is None:
                rdf = ET.SubElement(self.root, _q("rdf:RDF"))
            description = ET.SubElement(rdf, _q("rdf:Description"), {_q("rdf:about"): ""})
        return description

    @property
    def tags(self) -> list[str]:
        subject = self._find("dc:subject")
        if subject is None:
            return []
        return [
            li.text.strip()
            for container in subject
            for li in container.findall(_q("rdf:li"))
            if li.text and li.text.strip()
        ]

    @tags.setter
    def tags(self, tags: list[str]) -> None:
        """No tags remove dc:subject."""
        self.remove("dc:subject")
        if not tags:
            return
        subject = ET.SubElement(self._first_description(), _q("dc:subject"))
        bag = ET.SubElement(subject, _q("rdf:Bag"))
        for tag in tags:
            ET.SubElement(bag, _q("rdf:li")).text = tag

    @property
    def description(self) -> str:
        element = self._find("dc:description")
        if element is None:
            for candidate in self._descriptions():
                # Shorthand form: dc:description as an attribute.
                value = candidate.get(_q("dc:description"))
                if value:
                    return value
            return ""
        items = [li for container in element for li in container.findall(_q("rdf:li"))]
        for item in items:
            if item.get(_XML_LANG) == "x-default" and item.text:
                return item.text
        return next((item.text for item in items if item.text), element.text or "")

    @description.setter
    def description(self, text: str) -> None:
        """Replaces the x-default text, keeping the other languages. An empty
        text removes it, and dc:description once no language is left."""
        for description in self._descriptions():
            # Shorthand form: dc:description as an attribute
            if _q("dc:description") in description.attrib:
                del description.attrib[_q("dc:description")]
        element = self._find("dc:description")
        if element is None:
            element = ET.SubElement(self._first_description(), _q("dc:description"))
        alt = element.find(_q("rdf:Alt"))
        if alt is None:
            element.clear()
            alt = ET.SubElement(element, _q("rdf:Alt"))
        for li in alt.findall(_q("rdf:li")):
            if li.get(_XML_LANG) == "x-default":
                alt.remove(li)
        if text:
            li = ET.Element(_q("rdf:li"), {_XML_LANG: "x-default"})
            li.text = text
            alt.insert(0, li)
        if not alt.findall(_q("rdf:li")):
            self.remove("dc:description")

    def remove(self, name: str) -> None:
        """Removes `name`, element or shorthand attribute, from every rdf:Description."""
        for description in self._descriptions():
            for element in description.findall(_q(name)):
                description.remove(element)
            if _q(name) in description.attrib:
                del description.attrib[_q(name)]

    def save(self) -> None:
        ET.indent(self.root, space=" ")
        body = ET.tostring(self.root, encoding="unicode")
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(_XPACKET_BEGIN + body + _XPACKET_END, encoding="utf-8")
        tmp.replace(self.path)


def fold(tag: str) -> str:
    """Normalize a tag the way Mastodon does: accent-folded and lowercased."""
    decomposed = unicodedata.normalize("NFKD", tag)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def dedupe(tags: list[str]) -> list[str]:
    seen, kept = set(), []
    for tag in tags:
        key = fold(tag)
        if key and key not in seen:
            seen.add(key)
            kept.append(tag)
    return kept


def hashtags(tags: list[str]) -> str:
    return " ".join("#" + _NON_WORD_RE.sub("", tag) for tag in dedupe(tags))


def write_json(path: pathlib.Path, data: object) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fd:
        json.dump(data, fd, indent=4, sort_keys=True, ensure_ascii=False)
        fd.write("\n")
    tmp.replace(path)


def child_environment() -> dict[str, str]:
    """The environment of this process, without the access tokens."""
    return {key: value for key, value in os.environ.items() if not key.startswith("POSTER_")}


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run, with the environment of child_environment() unless env is given."""
    kwargs.setdefault("env", child_environment())
    return subprocess.run(args, **kwargs)


def request(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    """An HTTP request that fails loudly unless it succeeds."""
    response = session.request(method, url, timeout=300, **kwargs)
    if not response.ok:
        raise MnemographeError(f"{method} {url} returned {response.status_code}: {response.text[:500]}")
    return response


class PostRecord:
    """The files that record the post of a photo to a network, next to it.

    The pending marker is written right before the call that makes the post
    public, and removed once the json, the API responses, is written. A
    marker left by a crash stops later posts to that network: the photo may
    or may not be public.
    """

    def __init__(self, image: pathlib.Path, network: str) -> None:
        self.json = image.with_suffix(f".{network}.json")
        self.marker = image.with_suffix(f".{network}.pending")

    def pending(self, known: dict) -> None:
        write_json(self.marker, known)

    def posted(self, payload: dict) -> None:
        write_json(self.json, payload)
        self.marker.unlink()


def check_no_pending_post(images: list[pathlib.Path], network: str) -> None:
    """Fails on the marker of a post to the network that did not finish."""
    for image in images:
        record = PostRecord(image, network)
        if record.marker.exists():
            raise MnemographeError(
                f"a post of {image.name} to {network} did not finish: check {network} for {image.name}. "
                f"If it is posted, write {record.json} by hand. In both cases, delete {record.marker}."
            )


def check_token(token: str, origin: str) -> str:
    """token, if it looks like one. The error never shows it."""
    if not _TOKEN_RE.fullmatch(token):
        raise MnemographeError(f"{origin} is not a token: empty, or with other characters than letters, digits, ., _ and -")
    return token


def api_token(name: str) -> str:
    variable = "POSTER_" + _NON_WORD_RE.sub("_", name).upper() + "_API_TOKEN"
    if variable not in os.environ:
        raise MnemographeError(f"{variable} is not set: export it with the {name} access token")
    return check_token(os.environ[variable], variable)


class Mastodon:
    """The Mastodon destination: posts a status."""

    # Mastodon has no hashtag limit of its own
    max_hashtags = math.inf

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.instance = config["instance"].rstrip("/")
        self.visibility = config["visibility"]
        self.language = config["language"]
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "mnemographe.py (+https://charlesfleche.net)"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        return request(self.session, method, f"{self.instance}{path}", **kwargs)

    def prepare(self) -> None:
        self.session.headers["Authorization"] = f"Bearer {api_token(self.name)}"

    def post(self, image: pathlib.Path, text: str, description: str, record: PostRecord) -> dict:
        mimetype = mimetypes.guess_type(image.name)[0]
        with image.open("rb") as fd:
            response = self._request(
                "POST",
                "/api/v2/media",
                files={"file": (image.name, fd, mimetype)},
                data={"description": description} if description else None,
            )
        media = response.json()
        if response.status_code == 202:
            media = self._wait_media(media["id"])
        record.pending({"media": media})
        status = self._request(
            "POST",
            "/api/v1/statuses",
            json={
                "status": text,
                "media_ids": [media["id"]],
                "visibility": self.visibility,
                "language": self.language,
            },
            # The same for a given photo: Mastodon answers a retry within an
            # hour with the first post
            headers={"Idempotency-Key": f"mnemographe-{self.name}-{image.stem}"},
        ).json()
        record.posted(status)
        return status

    def _wait_media(self, media_id: str, timeout: float = 120) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            response = self._request("GET", f"/api/v1/media/{media_id}")
            if response.status_code == 200:
                return response.json()
            if time.monotonic() > deadline:
                raise MnemographeError(f"media {media_id} was still processing after {timeout:g}s")
            time.sleep(2)

    def post_url(self, payload: dict) -> str:
        return payload["url"]


def write_state(path: pathlib.Path, state: dict) -> None:
    """Replaces path with the json of state, readable by its owner only."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        os.fchmod(file.fileno(), 0o600)
        json.dump(state, file)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)


def read_state(path: pathlib.Path) -> dict:
    """The state write_state wrote, if the file is still readable by its owner only."""
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise MnemographeError(f"{path} must have mode 0600")
    with path.open(encoding="utf-8") as file:
        return json.load(file)


class InstagramLoginError(MnemographeError):
    pass


def refuse_challenge(username: str, *args: object) -> str:
    """instagrapi's challenge and password handlers: never act on a challenge, nor wait on stdin."""
    raise InstagramLoginError(
        f"Instagram asks to confirm a login of {username}: approve it in the Instagram app, then run again"
    )


def instagram_error(error: Exception) -> str:
    """The type and message of an instagrapi error, without the Instagram response it may hold."""
    return f"{type(error).__name__}: {str(getattr(error, 'message', '') or '')[:200]}"


class OneShotClient(instagrapi.Client):
    """instagrapi's Client, which sends the request that publishes a post once only.

    instagrapi resends a request after a timeout or an incomplete read: the
    post may then be published twice.
    """

    _publish_sent = False

    def _send_private_request(self, endpoint, *args, **kwargs):
        if endpoint == "media/configure/":
            if self._publish_sent:
                raise MnemographeError("instagrapi tried to send the post again: it may be public already")
            self._publish_sent = True
        return super()._send_private_request(endpoint, *args, **kwargs)


def secret(variable: str) -> str:
    """The value of the environment variable, which must be set and not empty. Errors never show it."""
    value = os.environ.get(variable, "")
    if not value:
        raise MnemographeError(f"{variable} is not set: export it")
    return value


class Instagram:
    """The Instagram destination, through instagrapi: Instagram's private API.

    It logs in as the account, with POSTER_INSTAGRAM_PASSWORD and, when
    the account has two-factor authentication, the TOTP seed of
    POSTER_INSTAGRAM_TOTP_SEED. The session, which stands for the password,
    is kept in instagram-session.json, at the root of the repository and
    ignored by git (mode 0600), so it logs in again only when Instagram ends
    the session. A login that Instagram asks to confirm fails: approve it in
    the Instagram app, then run again.
    """

    # Instagram's caption limit
    max_hashtags = 30

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.username = config["username"]
        self.session = _REPO_ROOT / f"{self.name}-session.json"
        self.client: instagrapi.Client | None = None

    def prepare(self) -> None:
        """Logs in, also when nothing is left to post, so the session stays in use."""
        password = secret("POSTER_INSTAGRAM_PASSWORD")
        # Instagram shows the seed in groups of 4
        totp_seed = os.environ.get("POSTER_INSTAGRAM_TOTP_SEED", "").replace(" ", "")
        client = OneShotClient()
        # A challenge fails at once: no request to Instagram, no prompt
        client.with_challenge_flow = False
        client.challenge_code_handler = refuse_challenge
        client.change_password_handler = refuse_challenge
        # Pauses between private API calls, as the app does
        client.delay_range = [1, 3]

        def settings(values: dict) -> None:
            client.set_settings(values)
            # No HTTP retry: a resent request could publish a post twice
            client.set_retry_config(session_retry_total=0)

        settings(read_state(self.session) if self.session.exists() else {})

        def login() -> None:
            code = client.totp_generate_code(totp_seed) if totp_seed else ""
            client.login(self.username, password, verification_code=code)

        try:
            login()
            # login() trusts a stored session: check it, and log in again,
            # as the same device, when Instagram ended it
            try:
                client.account_info()
            except instagrapi.exceptions.LoginRequired:
                uuids = client.get_settings()["uuids"]
                settings({})
                client.set_uuids(uuids)
                login()
        except instagrapi.exceptions.ClientError as error:
            raise InstagramLoginError(f"the {self.name} login of {self.username} failed: {instagram_error(error)}") from None
        write_state(self.session, client.get_settings())
        self.client = client

    def post(self, image: pathlib.Path, text: str, description: str, record: PostRecord) -> dict:
        assert self.client is not None, "prepare() first"
        record.pending({"username": self.username})
        # custom_accessibility_caption: the alt text field of the app
        extra = {"custom_accessibility_caption": description} if description else {}
        try:
            media = self.client.photo_upload(image, text, extra_data=extra)
        except instagrapi.exceptions.ClientError as error:
            # The marker stays: the post may be public
            raise MnemographeError(f"the {self.name} post of {image.name} failed: {instagram_error(error)}") from None
        # Not the rest: the viewer's flags, expiring image URLs, linked accounts
        payload = media.model_dump(mode="json", include={"pk", "id", "code", "taken_at", "caption_text", "accessibility_caption"})
        record.posted(payload)
        return payload

    def post_url(self, payload: dict) -> str:
        return f"https://www.instagram.com/p/{payload['code']}/"


_DESTINATION_TYPES = {"mastodon": Mastodon, "instagram": Instagram}


@dataclasses.dataclass
class Config:
    images: pathlib.Path
    destinations: dict

    @classmethod
    def load(cls, path: pathlib.Path) -> "Config":
        with path.open(encoding="utf-8") as fd:
            data = yaml.safe_load(fd)
        return cls(
            images=(path.parent / data["images"]).resolve(),
            destinations=data["destinations"],
        )

    def destination(self, name: str):
        config = self.destinations[name]
        return _DESTINATION_TYPES[config["type"]](name, config)

    def images_of(self) -> list[pathlib.Path]:
        images = [p for p in self.images.iterdir() if p.suffix.lower() in _IMAGE_SUFFIXES]
        return sorted(images, key=lambda p: p.name)


def is_posted(image: pathlib.Path, network: str) -> bool:
    return PostRecord(image, network).json.exists()


def publish_queue(config: Config, network: str) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """The photos not posted to the network yet: the tagged ones in publish order, and the untagged ones."""
    pending = [image for image in config.images_of() if not is_posted(image, network)]
    tagged = [image for image in pending if Xmp.for_image(image).tags]
    return tagged, [image for image in pending if image not in tagged]


def post(config: Config, network: str, dry_run: bool) -> None:
    network_config = config.destinations[network]
    destination = config.destination(network)
    if not dry_run:
        check_no_pending_post(config.images_of(), network)
        pull_and_push(config.images)
        destination.prepare()
    tagged, untagged = publish_queue(config, network)
    if not tagged:
        print(f"no tagged photo left for {network}, {photos(len(untagged))} to tag")
        if not dry_run:
            notify(
                f"No mnémographe left for {network}",
                f"Tag more photos: {photos(len(untagged))} to tag.",
                "mnemographe,warning",
            )
        return

    image = tagged[0]
    xmp = Xmp.for_image(image)
    tags = dedupe(network_config["default_tags"] + xmp.tags)
    if len(tags) > destination.max_hashtags:
        raise MnemographeError(
            f"{image.name} has {len(tags)} hashtags with the default ones, "
            f"{network} takes {destination.max_hashtags} at most: remove some of its tags"
        )
    text = hashtags(tags)
    print(f"{image.name} ({len(tagged)} tagged left)")
    print(f"  {text}")
    print(f"  alt: {xmp.description or '(none)'}")
    if dry_run:
        return

    record = PostRecord(image, network)
    payload = destination.post(image, text, xmp.description, record)
    git("add", "--", str(record.json))
    git("commit", "--message", f"Post {image.name} to {network}", "--", str(record.json))
    git("pull", "--rebase")
    git("push")
    url = destination.post_url(payload)
    print(f"  posted: {url}")
    notify(f"{image.name} posted to {network}", url, "mnemographe,outbox_tray")


def cmd_post(args: argparse.Namespace, config: Config) -> None:
    if args.dry_run:
        post(config, args.network, dry_run=True)
        return
    # Two networks may post at the same time from the same clone
    with repository_lock():
        post(config, args.network, dry_run=False)


def cmd_queue(args: argparse.Namespace, config: Config) -> None:
    tagged, untagged = publish_queue(config, args.network)
    for image in tagged:
        print(image.name, " ".join(Xmp.for_image(image).tags))
    print(f"{photos(len(tagged))} tagged and {photos(len(untagged))} untagged left for {args.network}")


class InboxError(MnemographeError):
    """INBOX holds files that ingest refuses: nothing was moved."""


def notify(title: str, message: str, tags: str) -> None:
    # --option=value: a value starting with a dash is not read as an option
    run(["ntfy-publish", f"--tags={tags}", f"--title={title}", f"--message={message}"], check=True)


def git(*args: str) -> None:
    run(["git", "-C", str(_REPO_ROOT), *args], check=True)


@contextlib.contextmanager
def repository_lock():
    """Serializes the commands that write, commit and push in the repository."""
    git_dir = run(
        ["git", "-C", str(_REPO_ROOT), "rev-parse", "--absolute-git-dir"], check=True, capture_output=True, text=True
    ).stdout.strip()
    with open(pathlib.Path(git_dir) / "mnemographe.lock", "w") as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield


def pull_and_push(gallery: pathlib.Path) -> None:
    """Pulls, and pushes the commits a previous run could not push.

    Fails on any uncommitted file of the gallery, like a post json left by a
    crash: it must not be forgotten.
    """
    status = run(
        ["git", "-C", str(_REPO_ROOT), "status", "--porcelain", "-z", "--untracked-files=all", "--", str(gallery)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    uncommitted = [entry for entry in status.split("\0") if entry]
    if uncommitted:
        raise MnemographeError(f"commit or remove these files of the gallery first: {', '.join(uncommitted)}")
    git("pull", "--rebase")
    git("push")


def photos(count: int) -> str:
    return f"{count} photo" if count == 1 else f"{count} photos"


def check_mirror(mirror: pathlib.Path, gallery: pathlib.Path) -> pathlib.Path:
    """MIRROR, resolved, once it is safe to mirror the gallery into with rsync --delete."""
    if mirror.is_symlink():
        raise MnemographeError(f"mirror {mirror} is a symbolic link")
    mirror = mirror.resolve()
    if not mirror.is_dir():
        raise MnemographeError(f"mirror {mirror} is not an existing directory")
    if mirror.is_relative_to(_REPO_ROOT):
        raise MnemographeError(f"mirror {mirror} is inside the repository {_REPO_ROOT}")
    if _REPO_ROOT.is_relative_to(mirror):
        raise MnemographeError(f"mirror {mirror} holds the repository {_REPO_ROOT}")
    # rsync --delete would delete them: a gallery mirror only holds files
    names = [path.name for path in mirror.iterdir()]
    directories = sorted(name for name in names if (mirror / name).is_dir())
    if directories:
        raise MnemographeError(f"mirror {mirror} holds directories: {', '.join(directories)}")
    # As publish.sh: a mirror mostly of other files is another folder
    gallery_names = {path.name for path in gallery.iterdir()}
    foreign = [name for name in names if name not in gallery_names]
    if len(foreign) > len(names) / 2:
        raise MnemographeError(
            f"mirror {mirror}: {len(foreign)} of its {len(names)} files are not in the gallery, "
            "it is not a gallery mirror"
        )
    return mirror


def mirror_gallery(gallery: pathlib.Path, mirror: pathlib.Path) -> None:
    """Makes MIRROR a copy of the gallery, deleting what the gallery does not hold."""
    mirror = check_mirror(mirror, gallery)
    # rsync works in the checked directory itself, even if its path changes:
    # Syncthing writes the phone's changes there, it is not only ours
    fd = os.open(mirror, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        run(
            ["rsync", "--archive", "--delete", f"{gallery}/", "./"],
            cwd=f"/proc/self/fd/{fd}",
            pass_fds=(fd,),
            check=True,
        )
    finally:
        os.close(fd)


def exif_metadata(paths: list[pathlib.Path]) -> dict[pathlib.Path, dict]:
    """What exiftool reads of each photo: file type, size, dates and problems."""
    result = run(
        ["exiftool", "-json", "-d", _RENAME_DATE_FORMAT, "-Error", "-Warning", "-FileType", "-ImageWidth", "-ImageHeight"]
        + [f"-{tag}" for tag in _RENAME_DATE_TAGS]
        + [str(path) for path in paths],
        # Not check=True: exiftool exits with 1 when it cannot read a file,
        # which is a problem of that file, found in its JSON
        capture_output=True,
        text=True,
    )
    metadata = {pathlib.Path(entry["SourceFile"]): entry for entry in json.loads(result.stdout)}
    if set(metadata) != set(paths):
        raise MnemographeError(f"exiftool did not read every photo: {result.stderr}")
    return metadata


def file_problem(path: pathlib.Path) -> str | None:
    """Why path is not a file ingest takes, from its name and type."""
    if path.name.startswith(".trashed-"):
        return "a file in the Android trash"
    if path.name.startswith(".syncthing.") and path.name.endswith(".tmp"):
        return "a Syncthing temporary file, of a sync not finished"
    if path.name.startswith("."):
        return "a hidden file"
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        return "a symbolic link"
    if stat.S_ISDIR(mode):
        return "a directory"
    if not stat.S_ISREG(mode):
        return "not a regular file"
    if path.suffix.lower() not in _IMAGE_SUFFIXES:
        return "not a .jpg or .jpeg file"
    return None


def photo_problem(metadata: dict) -> str | None:
    """Why exiftool's metadata of a photo is not a photo ingest takes."""
    if "Error" in metadata:
        return f"exiftool cannot read it: {metadata['Error']}"
    if metadata["FileType"] != "JPEG":
        return f"a {metadata['FileType']} file, not a JPEG"
    if "Warning" in metadata:
        return f"exiftool warns: {metadata['Warning']}"
    width, height = metadata["ImageWidth"], metadata["ImageHeight"]
    if max(width, height) > _MAX_SIDE:
        return f"larger than {_MAX_SIDE} px ({width}x{height})"
    if abs(width - height) > _SQUARE_TOLERANCE * max(width, height):
        return f"not square ({width}x{height})"
    return None


def rename_date(metadata: dict) -> str | None:
    """The date the photo is renamed after, formatted as _RENAME_DATE_FORMAT.

    exiftool renames after the last of its -filename< arguments whose tag
    exists, so the dates are taken in the reverse order of _RENAME_DATE_TAGS.
    """
    for tag in reversed(_RENAME_DATE_TAGS):
        if tag in metadata:
            date = str(metadata[tag])
            return date if _RENAME_DATE_RE.fullmatch(date) else None
    return None


def check_inbox(inbox: pathlib.Path, gallery_stems: set[str]) -> dict[pathlib.Path, str]:
    """The new name of every file of INBOX, or an InboxError listing every problem."""
    problems = []
    jpegs = []
    for path in sorted(inbox.iterdir()):
        problem = file_problem(path)
        if problem is None:
            jpegs.append(path)
        else:
            problems.append(f"{path.name}: {problem}")

    metadata_of = exif_metadata(jpegs) if jpegs else {}
    new_names = {}
    sources_of_stem: dict[str, list[pathlib.Path]] = {}
    for path in jpegs:
        metadata = metadata_of[path]
        problem = photo_problem(metadata)
        if problem is not None:
            problems.append(f"{path.name}: {problem}")
            continue
        date = rename_date(metadata)
        if date is None:
            problems.append(f"{path.name}: no EXIF date ({', '.join(_RENAME_DATE_TAGS)})")
            continue
        if date in gallery_stems:
            problems.append(f"{path.name}: {date} is already in the gallery")
        sources_of_stem.setdefault(date, []).append(path)
        new_names[path] = f"{date}{path.suffix.lower()}"
    for stem, sources in sorted(sources_of_stem.items()):
        if len(sources) > 1:
            problems.append(f"{', '.join(p.name for p in sources)}: would all be named {stem}")

    if problems:
        raise InboxError(f"Nothing was moved from {inbox}:\n" + "\n".join(problems))
    return new_names


def ingest(
    config: Config, inbox: pathlib.Path, mirror: pathlib.Path, publish_destination: str | None, autotag_unit: str | None
) -> None:
    with repository_lock():
        gallery = config.images
        check_mirror(mirror, gallery)
        pull_and_push(gallery)
        try:
            new_names = check_inbox(inbox, {image.stem for image in config.images_of()})
        except InboxError as error:
            notify("Mnémographe ingest failed", str(error), "mnemographe,warning")
            raise
        if not new_names:
            print(f"{inbox} is empty")
            return

        # Arguments, never a shell: file names cannot inject anything. The paths
        # are absolute, so none starts with a dash. In -d, %% is a literal %.
        destination_format = str(gallery).replace("%", "%%") + "/" + _RENAME_DATE_FORMAT + ".%%le"
        run(
            ["exiftool", "-d", destination_format]
            + [f"-filename<{tag}" for tag in _RENAME_DATE_TAGS]
            + [str(path) for path in new_names],
            # Not check=True: what moved and what stayed is checked below
        )
        moved = {source: gallery / name for source, name in new_names.items() if (gallery / name).is_file()}
        if len(moved) != len(new_names):
            raise MnemographeError(
                "exiftool did not move every photo, clean up by hand:\n"
                + "".join(f"moved {source.name} to {destination}\n" for source, destination in moved.items())
                + "".join(f"left {source}\n" for source in new_names if source not in moved)
            )

        paths = [str(path) for path in moved.values()]
        git("add", "--", *paths)
        git("commit", "--message", f"Add {photos(len(paths))} to mnémographe", "--", *paths)
        git("pull", "--rebase")
        git("push")

        publish_blog(publish_destination)
        # Last: a problem on the phone side never holds back the blog
        mirror_gallery(gallery, mirror)

        untagged = sum(1 for image in config.images_of() if not Xmp.for_image(image).tags)
        notify(
            f"{photos(len(paths))} added to the mnémographe",
            f"Blog published, phone gallery updated. {photos(untagged)} to tag.",
            "mnemographe,frame_with_picture",
        )
    if autotag_unit is not None:
        # Without waiting: the watch goes on, and a failure of the unit
        # notifies on its own. Started on a running unit, it does nothing:
        # autotag then tags this ingest's photos in its next round
        run(["systemctl", "--user", "start", "--no-block", autotag_unit], check=True)


def publish_blog(publish_destination: str | None) -> None:
    """Builds the site and publishes it with bin/publish.sh."""
    # publish.sh and uv pip run without the environment of this script, which
    # `uv run --script` sets: they use the repository's .venv
    environment = {key: value for key, value in child_environment().items() if key != "VIRTUAL_ENV"}
    run(
        ["uv", "pip", "install", "--quiet", "--python", str(_REPO_ROOT / ".venv" / "bin" / "python"),
         "--requirement", str(_REPO_ROOT / "requirements.txt")],
        check=True,
        env=environment,
    )
    publish = [str(_REPO_ROOT / "bin" / "publish.sh")]
    if publish_destination is not None:
        publish.append(publish_destination)
    run(publish, check=True, env=environment)


def cmd_ingest(args: argparse.Namespace, config: Config) -> None:
    ingest(config, args.inbox.resolve(), args.mirror, args.publish_destination, args.autotag_unit)


def added_times(gallery: pathlib.Path) -> dict[str, int]:
    """The author time of the commit that added each file of the gallery, by file name.

    A renamed file keeps the time it was added under its first name.
    """
    result = run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false", "log", "--reverse", "-M",
         "--name-status", "--format=%x00%at", "--", str(gallery)],
        check=True,
        capture_output=True,
        text=True,
    )
    added: dict[str, int] = {}
    for line in result.stdout.splitlines():
        if line.startswith("\0"):
            commit_time = int(line.removeprefix("\0"))
            continue
        if not line:
            continue
        status, *paths = line.split("\t")
        names = [pathlib.PurePosixPath(path).name for path in paths]
        if status == "A":
            added[names[0]] = commit_time
        elif status.startswith("R"):
            added[names[1]] = added.pop(names[0])
        elif status == "D":
            del added[names[0]]
    return added


def same_hashtag(tags: list[str]) -> list[str]:
    """The tags that fold() to the same hashtag as another one."""
    folded = [fold(tag) for tag in tags]
    return [tag for tag, key in zip(tags, folded) if folded.count(key) > 1]


def posted_column(image: pathlib.Path) -> str:
    return "".join(letter if is_posted(image, network) else "-" for network, letter in _POSTED_COLUMN.items())


def tag_fields(xmp: "Xmp") -> tuple[list[str], str]:
    """The fields of xmp that the tag editor edits: its tags and its alt text."""
    return xmp.tags, xmp.description


def tags_file(images: list[pathlib.Path]) -> str:
    """The text the tag editor opens: one line per photo, after the header."""
    lines = []
    problems = []
    for image in images:
        xmp = Xmp.for_image(image)
        bad_tags = [tag for tag in xmp.tags if _NON_WORD_RE.search(tag)]
        if bad_tags:
            problems.append(f"{xmp.path.name}: tags with other characters than letters, digits and _: {' '.join(bad_tags)}")
        if same_hashtag(xmp.tags):
            problems.append(f"{xmp.path.name}: tags that are the same hashtag: {' '.join(same_hashtag(xmp.tags))}")
        if len(xmp.description.splitlines()) > 1:
            problems.append(f"{xmp.path.name}: alt text on several lines")
        line = " ".join([posted_column(image), image.name, *xmp.tags])
        if xmp.description:
            line += f" | {xmp.description}"
        lines.append(line + "\n")
    if problems:
        raise MnemographeError("The tag editor cannot show these sidecars, fix them by hand:\n" + "\n".join(problems))
    return _TAGS_FILE_HEADER + "".join(lines)


def parse_tags_file(text: str, images_by_name: dict[str, pathlib.Path]) -> dict[str, tuple[list[str], str]]:
    """The tags and alt text of each photo of the edited text, or every error in it."""
    entries: dict[str, tuple[list[str], str]] = {}
    line_numbers: dict[str, int] = {}
    errors = []
    for number, line in enumerate(unicodedata.normalize("NFC", text).splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head, _, alt = line.partition("|")
        words = head.split()
        if len(words) < 2 or not _POSTED_RE.fullmatch(words[0]):
            errors.append(f"line {number}: not <posted> <file> ...: {line}")
            continue
        name, tags = words[1], words[2:]
        if name not in images_by_name:
            errors.append(f"line {number}: no photo {name} in the gallery")
        elif name in entries:
            errors.append(f"line {number}: {name} is on line {line_numbers[name]} already")
        bad_tags = [tag for tag in tags if _NON_WORD_RE.search(tag)]
        if bad_tags:
            errors.append(f"line {number}: tags with other characters than letters, digits and _: {' '.join(bad_tags)}")
        if same_hashtag(tags):
            errors.append(f"line {number}: tags that are the same hashtag: {' '.join(same_hashtag(tags))}")
        if _NOT_XML_RE.search(alt):
            errors.append(f"line {number}: the alt text holds characters XML does not allow")
        line_numbers.setdefault(name, number)
        entries[name] = (tags, alt.strip())
    if errors:
        raise MnemographeError("\n".join(errors))
    if not entries:
        raise MnemographeError("no photo line")
    return entries


def edit(path: pathlib.Path) -> None:
    """Opens path in git's editor, and runs it as git does: the setting may hold options."""
    editor = run(
        ["git", "-C", str(_REPO_ROOT), "var", "GIT_EDITOR"], check=True, capture_output=True, text=True
    ).stdout.strip()
    status = run(["sh", "-c", f'{editor} "$@"', editor, str(path)]).returncode
    if status != 0:
        raise MnemographeError(f"the editor exited with status {status}: nothing changed, the file is kept: {path}")


def cmd_tag(args: argparse.Namespace, config: Config) -> None:
    gallery = config.images
    # Not while the editor is open: the watch may ingest meanwhile
    with repository_lock():
        mirror = check_mirror(args.mirror, gallery)
        pull_and_push(gallery)
        images = config.images_of()
        added = added_times(gallery)
    # pull_and_push() refused uncommitted files: every photo has a time
    newest_first = sorted(images, key=lambda image: (added[image.name], image.name), reverse=True)
    text = tags_file(newest_first)
    # What the editor shows: the edits are the differences from it
    shown = {image.name: tag_fields(Xmp.for_image(image)) for image in images}
    # Named like git's own files, so editors open it as plain text. Kept
    # when anything fails, so the edits are never lost
    directory = pathlib.Path(tempfile.mkdtemp(prefix="mnemographe-tag-"))
    path = directory / _TAGS_FILE_NAME
    path.write_text(text, encoding="utf-8")
    edit(path)
    try:
        entries = parse_tags_file(path.read_text(encoding="utf-8"), {image.name: image for image in images})
    except MnemographeError as error:
        raise MnemographeError(f"{error}\nNothing written, the edited file is kept: {path}") from None

    edits = {name: fields for name, fields in entries.items() if fields != shown[name]}
    changed = save_tag_edits(gallery, mirror, edits, shown, f"the edited file is kept: {path}")
    shutil.rmtree(directory)
    if not changed:
        print("nothing changed")
        return
    print(f"tagged {photos(len(changed))}, pushed, mirrored to {mirror}")


def save_tag_edits(
    gallery: pathlib.Path,
    mirror: pathlib.Path,
    edits: dict[str, tuple[list[str], str]],
    shown: dict[str, tuple[list[str], str]],
    kept: str,
) -> list[str]:
    """Writes the tags and alt texts of edits, commits, pushes and mirrors: the sidecars written.

    shown holds the fields each edited photo had when the edits started: a
    photo changed since then stops everything, and kept says what is left to
    retry with.
    """
    with repository_lock():
        # Another tag session, or another clone, may have tagged meanwhile:
        # never overwrite its work
        pull_and_push(gallery)
        conflicts = [name for name in edits if tag_fields(Xmp.for_image(gallery / name)) != shown[name]]
        if conflicts:
            raise MnemographeError(f"changed meanwhile: {', '.join(sorted(conflicts))}\nNothing written, {kept}")
        changed = []
        for name, (tags, alt) in edits.items():
            xmp = Xmp.for_image(gallery / name)
            # Only the changed field: the other keeps its exact form
            if tags != xmp.tags:
                xmp.tags = tags
            if alt != xmp.description:
                xmp.description = alt
            xmp.save()
            changed.append(str(xmp.path))
        if not changed:
            return changed

        git("add", "--", *changed)
        git("commit", "--message", f"Tag {photos(len(changed))} in mnémographe", "--", *changed)
        git("pull", "--rebase")
        git("push")
        mirror_gallery(gallery, mirror)
    return changed


def untagged(images: list[pathlib.Path]) -> dict[str, tuple[list[str], str]]:
    """The tags and alt text of the photos missing either."""
    fields = {image.name: tag_fields(Xmp.for_image(image)) for image in images}
    return {name: (tags, alt) for name, (tags, alt) in fields.items() if not tags or not alt}


def small_copy(image: pathlib.Path) -> pathlib.Path:
    """The site build's 320 px copy of image, else image itself."""
    copy = _REPO_ROOT / "build" / "dist" / image.parent.name.split("-", 3)[-1] / f"{image.stem}.320x.jpeg"
    return copy if copy.is_file() else image


def saturation(image: pathlib.Path) -> float:
    """The mean HSL saturation of image."""
    return float(
        run(
            ["magick", "-define", "jpeg:size=320x320", str(small_copy(image)), "-resize", "160x",
             "-colorspace", "HSL", "-channel", "G", "-separate", "+channel", "-format", "%[fx:mean]", "info:"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )


def autotag_facts(images: list[pathlib.Path]) -> dict[str, dict]:
    """What Claude cannot see on a photo: its camera, position, and whether it is in color."""
    result = run(
        ["exiftool", "-json", "-n", "-Model", "-GPSLatitude", "-GPSLongitude"] + [str(image) for image in images],
        check=True,
        capture_output=True,
        text=True,
    )
    exif = {pathlib.Path(entry["SourceFile"]).name: entry for entry in json.loads(result.stdout)}
    facts = {}
    for image in images:
        entry = exif[image.name]
        position = (
            f"{entry['GPSLatitude']:.5f},{entry['GPSLongitude']:.5f}"
            if "GPSLatitude" in entry and "GPSLongitude" in entry
            else "no GPS"
        )
        facts[image.name] = {
            "camera": entry.get("Model", "unknown camera"),
            "position": position,
            "color": saturation(image) > _AUTOTAG_COLOR_SATURATION,
        }
    return facts


def contact_sheets(images: list[pathlib.Path], directory: pathlib.Path) -> list[str]:
    """Writes contact sheets of the photos in directory, each labeled with its number and stem: their names."""
    names = []
    for start in range(0, len(images), _AUTOTAG_SHEET_SIZE):
        name = f"sheet{start // _AUTOTAG_SHEET_SIZE + 1:02}.jpg"
        labeled = []
        for number, image in enumerate(images[start:start + _AUTOTAG_SHEET_SIZE], start=start + 1):
            labeled += ["-label", f"{number} {image.stem}", str(small_copy(image))]
        run(
            ["magick", "montage", "-define", "jpeg:size=600x600", *labeled,
             "-tile", "4x4", "-geometry", "300x300+4+4", "-pointsize", "18", str(directory / name)],
            check=True,
        )
        names.append(name)
    return names


def autotag_prompt(images: list[pathlib.Path], shown: dict, facts: dict, sheets: list[str]) -> str:
    lines = []
    for number, image in enumerate(images, start=1):
        tags, alt = shown[image.name]
        missing = " and ".join(field for field, value in (("tags", tags), ("alt text", alt)) if not value)
        date = f"{image.stem[0:4]}-{image.stem[4:6]}-{image.stem[6:8]}"
        fact = facts[image.name]
        lines.append(
            f"{number} | {image.name} | {date} | {fact['camera']} | {fact['position']} | "
            f"{'color' if fact['color'] else 'black and white'} | {missing}"
        )
    return f"""\
Tag these new mnémographe photos in unattended mode: follow the conventions and
the "Unattended mode" section of the mnemographe-tag skill, in your system prompt.

Read the contact sheets {', '.join(sheets)}, in the current directory. Each
photo on them is labeled with its number and its stem.

One photo per line: number | file | date | camera | GPS position | color or
black and white, measured | what it is missing:

{chr(10).join(lines)}
"""


def ask_claude(prompt: str, directory: pathlib.Path) -> dict:
    """Claude's answer to prompt, with the skill as system prompt, as _AUTOTAG_SCHEMA.

    Claude only reads the files of directory, its working directory: the
    photos may show text written as instructions, and the alt texts are
    public. No user settings, hooks, plugins, MCP servers or skills.
    """
    output = directory / "claude.json"
    with output.open("w", encoding="utf-8") as fd:
        status = run(
            ["claude", "--print", prompt,
             "--append-system-prompt-file", str(_SKILL_PATH),
             "--tools", "Read", "--permission-mode", "dontAsk",
             "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
             "--no-session-persistence",
             "--output-format", "json", "--json-schema", json.dumps(_AUTOTAG_SCHEMA)],
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=fd,
            timeout=_AUTOTAG_TIMEOUT,
        ).returncode
    try:
        result = json.loads(output.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise MnemographeError(f"claude exited with status {status}, its output is not JSON: {output}") from None
    if status != 0 or result.get("is_error") or "structured_output" not in result:
        raise MnemographeError(f"claude exited with status {status} and no answer: {result.get('result')}\nSee {output}")
    print(f"claude answered in {result['duration_ms'] / 1000:.0f} s, ${result['total_cost_usd']:.2f}", flush=True)
    return result["structured_output"]


def autotag_edits(
    images: list[pathlib.Path], shown: dict, facts: dict, answer: dict
) -> tuple[dict[str, tuple[list[str], str]], dict[str, str]]:
    """The tags and alt texts of answer that fill the missing fields, and the guesses, or every problem of answer."""
    problems = []
    by_name = {}
    for photo in answer["photos"]:
        if photo["file"] in by_name:
            problems.append(f"{photo['file']} answered twice")
        by_name[photo["file"]] = photo
    names = {image.name for image in images}
    problems += [f"{name} not answered" for name in sorted(names - set(by_name))]
    problems += [f"{name} answered, not asked" for name in sorted(set(by_name) - names)]
    lines, guesses = [], {}
    for image in images:
        photo = by_name.get(image.name)
        if photo is None:
            continue
        old_tags, old_alt = shown[image.name]
        tags = old_tags or photo["tags"]
        alt = old_alt or photo["alt"].strip()
        if not tags:
            problems.append(f"{image.name}: no tags")
        if not old_tags and facts[image.name]["color"] == ("BlackAndWhite" in tags):
            problems.append(f"{image.name}: black-and-white tags do not match the measured color: {' '.join(tags)}")
        if len(alt.splitlines()) != 1 or " / " not in alt:
            problems.append(f"{image.name}: the alt text is not one line, English / French: {alt!r}")
        lines.append(f"{posted_column(image)} {image.name} {' '.join(tags)} | {alt}\n")
        if photo["guesses"].strip():
            guesses[image.name] = photo["guesses"].strip()
    if problems:
        raise MnemographeError("Claude's answer is refused, nothing written:\n" + "\n".join(problems))
    # The checks of the tag editor
    edits = parse_tags_file("".join(lines), {image.name: image for image in images})
    return edits, guesses


def autotag_report(edits: dict[str, tuple[list[str], str]], guesses: dict[str, str]) -> str:
    report = []
    for name, (tags, alt) in edits.items():
        report.append(f"{name}: {alt}\n{' '.join(tags)}")
        if name in guesses:
            report[-1] += f"\nGuess: {guesses[name]}"
    return "\n\n".join(report)


def cmd_autotag(args: argparse.Namespace, config: Config) -> None:
    gallery = config.images
    done: set[str] = set()
    # A round per batch: an ingest during a round starts no other run, its
    # photos are left for the next round
    while True:
        with repository_lock():
            check_mirror(args.mirror, gallery)
            pull_and_push(gallery)
            shown = untagged(config.images_of())
        if not shown:
            break
        again = sorted(set(shown) & done)
        if again:
            raise MnemographeError(f"still missing tags or an alt text after a round: {', '.join(again)}")
        images = [gallery / name for name in sorted(shown)]
        print(f"tagging {photos(len(images))}: {', '.join(image.name for image in images)}", flush=True)
        # Kept when anything fails, with Claude's answer
        directory = pathlib.Path(tempfile.mkdtemp(prefix="mnemographe-autotag-"))
        facts = autotag_facts(images)
        sheets = contact_sheets(images, directory)
        answer = ask_claude(autotag_prompt(images, shown, facts, sheets), directory)
        try:
            edits, guesses = autotag_edits(images, shown, facts, answer)
        except MnemographeError as error:
            raise MnemographeError(f"{error}\nSee {directory / 'claude.json'}") from None
        report = autotag_report(edits, guesses)
        print(report, flush=True)
        save_tag_edits(gallery, args.mirror, edits, shown, f"run autotag again: {directory}")
        shutil.rmtree(directory)
        done |= set(shown)
        publish_blog(args.publish_destination)
        notify(
            f"Claude tagged {photos(len(edits))} of the mnémographe",
            f"Fix them with mnemographe-tag before they are posted.\n\n{report}",
            "mnemographe,label",
        )
    if not done:
        print("every photo has tags and an alt text")


def syncthing_config(inbox: pathlib.Path) -> tuple[str, str, str]:
    """The API key, and the id of the Syncthing folder holding INBOX and the path of INBOX in it."""
    root = ET.parse(_SYNCTHING_CONFIG_PATH).getroot()
    api_key = root.find("gui").find("apikey").text
    for folder in root.findall("folder"):
        folder_path = pathlib.Path(folder.get("path")).expanduser().resolve()
        if inbox.is_relative_to(folder_path) and inbox != folder_path:
            return api_key, folder.get("id"), inbox.relative_to(folder_path).as_posix()
    raise MnemographeError(f"{inbox} is not a subfolder of a Syncthing folder of {_SYNCTHING_CONFIG_PATH}")


def watch_events(events: list[dict], folder: str, prefix: str, pending: bool, on_idle) -> bool:
    """Calls on_idle when the folder is idle after a change in prefix: whether a change is still pending."""
    for event in events:
        data = event["data"]
        if data["folder"] != folder:
            continue
        if event["type"] == "ItemFinished" and (data["item"] == prefix or data["item"].startswith(prefix + "/")):
            pending = True
        elif event["type"] == "StateChanged" and data["to"] == "idle" and pending:
            on_idle()
            pending = False
    return pending


def cmd_watch(args: argparse.Namespace, config: Config) -> None:
    inbox = args.inbox.resolve()
    check_mirror(args.mirror, config.images)
    api_key, folder, prefix = syncthing_config(inbox)
    session = requests.Session()
    session.headers["X-API-Key"] = api_key

    def events(since: int, **params) -> list[dict]:
        # Event ids count per event mask: every request uses the same one.
        # The timeout is longer than the 60 s long poll
        response = session.get(
            _SYNCTHING_URL + "/rest/events",
            params={"since": since, "events": _SYNCTHING_EVENTS, **params},
            timeout=90,
        )
        response.raise_for_status()
        return response.json()

    def on_idle() -> None:
        try:
            ingest(config, inbox, args.mirror, args.publish_destination, args.autotag_unit)
        except InboxError as error:
            # Already notified: waits for the next change in the inbox
            print(f"error: {error}", file=sys.stderr)

    # The last event before looking at the inbox, so no later change is missed
    latest = events(0, limit=1, timeout=1)
    since = latest[-1]["id"] if latest else 0
    pending = any(inbox.iterdir())
    if pending:
        response = session.get(_SYNCTHING_URL + "/rest/db/status", params={"folder": folder}, timeout=90)
        response.raise_for_status()
        if response.json()["state"] == "idle":
            on_idle()
            pending = False
    print(f"watching {prefix} in Syncthing folder {folder}, from event {since}", flush=True)
    while True:
        new_events = events(since)
        if new_events:
            since = new_events[-1]["id"]
        pending = watch_events(new_events, folder, prefix, pending, on_idle)


def main() -> int:
    parser = argparse.ArgumentParser(prog="mnemographe", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(required=True)

    post = subparsers.add_parser("post", help="post the oldest tagged photo not posted to NETWORK yet")
    post.add_argument("network")
    post.add_argument(
        "-n", "--dry-run", action="store_true", help="only print what would be posted: no git, no network, no token"
    )
    post.set_defaults(func=cmd_post)

    queue = subparsers.add_parser("queue", help="list the tagged photos NETWORK will get, in publish order")
    queue.add_argument("network")
    queue.set_defaults(func=cmd_queue)

    for name, func, help in (
        ("ingest", cmd_ingest, "move the photos of INBOX into the gallery, commit, push and publish"),
        ("watch", cmd_watch, "ingest INBOX each time Syncthing has synced a change in it"),
    ):
        command = subparsers.add_parser(name, help=help)
        command.add_argument("inbox", type=pathlib.Path)
        command.add_argument(
            "--mirror",
            type=pathlib.Path,
            required=True,
            help="existing directory to mirror the gallery to, e.g. a Syncthing folder of the phone",
        )
        command.add_argument(
            "--publish-destination",
            help="rsync destination of bin/publish.sh, its own default if not given",
        )
        command.add_argument(
            "--autotag-unit",
            help="systemd user unit to start, without waiting, after an ingest: the one running autotag",
        )
        command.set_defaults(func=func)

    autotag = subparsers.add_parser(
        "autotag", help="have Claude tag the photos missing tags or an alt text, then commit, push and publish"
    )
    autotag.add_argument(
        "--mirror",
        type=pathlib.Path,
        required=True,
        help="existing directory to mirror the gallery to, e.g. a Syncthing folder of the phone",
    )
    autotag.add_argument(
        "--publish-destination",
        help="rsync destination of bin/publish.sh, its own default if not given",
    )
    autotag.set_defaults(func=cmd_autotag)

    tag = subparsers.add_parser("tag", help="edit the tags and alt texts of the photos in git's editor")
    tag.add_argument(
        "--mirror",
        type=pathlib.Path,
        required=True,
        help="existing directory to mirror the gallery to, e.g. a Syncthing folder of the phone",
    )
    tag.set_defaults(func=cmd_tag)

    args = parser.parse_args()
    try:
        args.func(args, Config.load(_CONFIG_PATH))
    except MnemographeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
