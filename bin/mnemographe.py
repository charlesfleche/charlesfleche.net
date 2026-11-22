#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pyyaml"]
# ///
"""mnemographe.py — ingest new photos into the mnémographe gallery, and post them.

The gallery is the folder named by `images` in mnemographe.yml, at the root of
the repository holding this script: content/page/2022-01-01-mnemographe.

ingest INBOX checks every file of INBOX, and fails before moving anything if
one is not a square JPEG with an EXIF date, or would collide with another
photo. It renames them after their date, %Y%m%d-%H%M%S.<lowercase extension>,
taken from DateTimeOriginal, else CreateDate, else GPSDateTime, and moves them
into the gallery. It then commits and pushes them, publishes the blog with
bin/publish.sh, and notifies through ntfy-publish. It works on the git
repository holding this script, after pulling it.

watch INBOX listens to the local Syncthing REST API, and runs ingest each time
the Syncthing folder holding INBOX is idle after a change in INBOX. INBOX is a
subfolder of a Syncthing folder, not a folder of its own.

post DESTINATION posts the oldest unposted photo, by file name. A photo counts
as posted to a destination once <stem>.<destination>.json — the REST payload
of the post — sits next to it. Tags and alt text live in an XMP sidecar
<stem>.xmp (dc:subject and dc:description), readable and writable by exiftool,
darktable and digiKam. A photo without tags is never posted: the script fails
loudly so the systemd unit shows as failed.

Destinations are configured in mnemographe.yml. Access tokens are read from the
environment only, never from the configuration file:
POSTER_<DESTINATION>_API_TOKEN, e.g. POSTER_MASTODON_API_TOKEN.

Usage:

    bin/mnemographe.py ingest ~/Syncthing/3a-Pictures/minbox
    bin/mnemographe.py watch ~/Syncthing/3a-Pictures/minbox
    bin/mnemographe.py post mastodon --dry-run          # what would be posted
    bin/mnemographe.py post mastodon                    # post it

The sidecars stay readable by other tools:

    exiftool -s -XMP-dc:Subject -ext xmp content/page/2022-01-01-mnemographe
"""

import argparse
import dataclasses
import json
import mimetypes
import os
import pathlib
import re
import stat
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET

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

    def _container(self, name: str) -> ET.Element:
        """The rdf:Description holding `name`, creating the element if needed."""
        for description in self._descriptions():
            if description.find(_q(name)) is not None:
                return description
        descriptions = self._descriptions()
        if not descriptions:
            rdf = self.root.find(_q("rdf:RDF"))
            if rdf is None:
                rdf = ET.SubElement(self.root, _q("rdf:RDF"))
            descriptions = [ET.SubElement(rdf, _q("rdf:Description"))]
            descriptions[0].set(_q("rdf:about"), "")
        return descriptions[0]

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
        description = self._container("dc:subject")
        subject = description.find(_q("dc:subject"))
        if subject is None:
            subject = ET.SubElement(description, _q("dc:subject"))
        subject.clear()
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
        container = self._container("dc:description")
        element = container.find(_q("dc:description"))
        if element is None:
            element = ET.SubElement(container, _q("dc:description"))
        element.clear()
        alt = ET.SubElement(element, _q("rdf:Alt"))
        li = ET.SubElement(alt, _q("rdf:li"))
        li.set(_XML_LANG, "x-default")
        li.text = text

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


def api_token(name: str) -> str:
    variable = "POSTER_" + _NON_WORD_RE.sub("_", name).upper() + "_API_TOKEN"
    token = os.environ.get(variable, "").strip()
    if not token:
        raise MnemographeError(f"{variable} is not set: export it with the {name} access token")
    return token


class Mastodon:
    """The Mastodon destination: posts a status."""

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.instance = config["instance"].rstrip("/")
        self.visibility = config["visibility"]
        self.language = config["language"]
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_token(name)}"
        self.session.headers["User-Agent"] = "mnemographe.py (+https://charlesfleche.net)"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = path if path.startswith("http") else f"{self.instance}{path}"
        response = self.session.request(method, url, timeout=300, **kwargs)
        if not response.ok:
            raise MnemographeError(f"{method} {url} returned {response.status_code}: {response.text[:500]}")
        return response

    def post(self, image: pathlib.Path, text: str, description: str) -> dict:
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
        return self._request(
            "POST",
            "/api/v1/statuses",
            json={
                "status": text,
                "media_ids": [media["id"]],
                "visibility": self.visibility,
                "language": self.language,
            },
            # Survives a retry after a crash between posting and writing the sidecar.
            headers={"Idempotency-Key": f"poster-{self.name}-{image.stem}"},
        ).json()

    def _wait_media(self, media_id: str, timeout: float = 120) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            response = self._request("GET", f"/api/v1/media/{media_id}")
            if response.status_code == 200:
                return response.json()
            if time.monotonic() > deadline:
                raise MnemographeError(f"media {media_id} was still processing after {timeout:g}s")
            time.sleep(2)


_DESTINATION_TYPES = {"mastodon": Mastodon}


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


def payload_path(image: pathlib.Path, destination: str) -> pathlib.Path:
    return image.with_suffix(f".{destination}.json")


def is_posted(image: pathlib.Path, destination: str) -> bool:
    return payload_path(image, destination).exists()


def cmd_post(args: argparse.Namespace, config: Config) -> None:
    name = args.destination
    destination_config = config.destinations[name]
    images = config.images_of()
    pending = [image for image in images if not is_posted(image, name)]
    if not pending:
        print(f"all {len(images)} images are already posted to {name}")
        return
    image = pending[0]
    xmp = Xmp.for_image(image)
    if not xmp.tags:
        raise MnemographeError(
            f"{image} has no tags\n"
            f"  tag it in its XMP sidecar: {xmp.path}"
        )
    text = hashtags(destination_config["default_tags"] + xmp.tags)
    description = xmp.description
    print(f"{image.name} ({len(pending)} left)")
    print(f"  {text}")
    if description:
        print(f"  alt: {description}")
    if args.dry_run:
        return
    payload = config.destination(name).post(image, text, description)
    write_json(payload_path(image, name), payload)
    print(f"  posted: {payload['url']}")


class InboxError(MnemographeError):
    """INBOX holds files that ingest refuses: nothing was moved."""


def notify(title: str, message: str, tags: str) -> None:
    # --option=value: a value starting with a dash is not read as an option
    subprocess.run(["ntfy-publish", f"--tags={tags}", f"--title={title}", f"--message={message}"], check=True)


def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(_REPO_ROOT), *args], check=True)


def photos(count: int) -> str:
    return f"{count} photo" if count == 1 else f"{count} photos"


def exif_metadata(paths: list[pathlib.Path]) -> dict[pathlib.Path, dict]:
    """What exiftool reads of each photo: file type, size, dates and problems."""
    result = subprocess.run(
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


def ingest(config: Config, inbox: pathlib.Path, publish_destination: str | None) -> None:
    # Pushes the commits a previous ingest could not push
    git("pull", "--rebase")
    git("push")
    gallery = config.images
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
    subprocess.run(
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

    # publish.sh and uv pip run without the environment of this script, which
    # `uv run --script` sets: they use the repository's .venv
    environment = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    subprocess.run(
        ["uv", "pip", "install", "--quiet", "--python", str(_REPO_ROOT / ".venv" / "bin" / "python"),
         "--requirement", str(_REPO_ROOT / "requirements.txt")],
        check=True,
        env=environment,
    )
    publish = [str(_REPO_ROOT / "bin" / "publish.sh")]
    if publish_destination is not None:
        publish.append(publish_destination)
    subprocess.run(publish, check=True, env=environment)

    untagged = sum(1 for image in config.images_of() if not Xmp.for_image(image).tags)
    notify(
        f"{photos(len(paths))} added to the mnémographe",
        f"Blog published. {photos(untagged)} to tag.",
        "mnemographe,frame_with_picture",
    )


def cmd_ingest(args: argparse.Namespace, config: Config) -> None:
    ingest(config, args.inbox.resolve(), args.publish_destination)


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
            ingest(config, inbox, args.publish_destination)
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

    post = subparsers.add_parser("post", help="post the next unposted image")
    post.add_argument("destination")
    post.add_argument("-n", "--dry-run", action="store_true")
    post.set_defaults(func=cmd_post)

    for name, func, help in (
        ("ingest", cmd_ingest, "move the photos of INBOX into the gallery, commit, push and publish"),
        ("watch", cmd_watch, "ingest INBOX each time Syncthing has synced a change in it"),
    ):
        command = subparsers.add_parser(name, help=help)
        command.add_argument("inbox", type=pathlib.Path)
        command.add_argument(
            "--publish-destination",
            help="rsync destination of bin/publish.sh, its own default if not given",
        )
        command.set_defaults(func=func)

    args = parser.parse_args()
    try:
        args.func(args, Config.load(_CONFIG_PATH))
    except MnemographeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
