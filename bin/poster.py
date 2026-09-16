#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pyyaml", "pillow", "imagehash"]
# ///
"""poster.py — post the next unposted image of a folder to Mastodon (and later, elsewhere).

Images are posted oldest first, by filename. An image counts as posted to a
destination once <stem>.<destination>.json — the REST payload of the post —
sits next to it. Tags and alt text live in an XMP sidecar <stem>.xmp
(dc:subject and dc:description), readable and writable by exiftool, darktable
and digiKam. An image without tags is never posted: the script fails loudly so
the systemd unit shows as failed.

Destinations are configured in poster.yml at the repository root. Access
tokens are read from the environment only, never from the configuration file:
POSTER_<DESTINATION>_API_TOKEN, e.g. POSTER_MASTODON_API_TOKEN.

Usage:

    bin/poster.py list mastodon                         # what needs tags next
    bin/poster.py list mastodon -u -p | xargs -d '\n' swayimg   # look at the untagged ones
    bin/poster.py tag IMAGE Vélo Bicycle Québec         # write <stem>.xmp
    bin/poster.py tag IMAGE --description "Alt text"    # alt text
    bin/poster.py tag IMAGE                             # show current tags
    bin/poster.py post mastodon --dry-run               # what would be posted
    bin/poster.py post mastodon                         # post it
    bin/poster.py import mastodon --dry-run             # match existing posts

`import` walks the destination's own history, downloads the images of every
post carrying the configured tag, matches them against the local folder with
perceptual hashes, and writes the sidecars of the images already posted.

The sidecars stay readable by other tools:

    exiftool -s -XMP-dc:Subject -ext xmp content/page/2022-01-01-mnemographe

Systemd, as a user unit — ~/.config/systemd/user/poster@.service:

    [Service]
    Type=oneshot
    EnvironmentFile=%h/.config/poster/env      # POSTER_MASTODON_API_TOKEN=..., mode 600
    WorkingDirectory=%h/src/charlesfleche.net
    ExecStart=%h/src/charlesfleche.net/bin/poster.py post %i

and ~/.config/systemd/user/poster@.timer:

    [Timer]
    OnCalendar=daily
    Persistent=true

    [Install]
    WantedBy=timers.target

then `systemctl --user enable --now poster@mastodon.timer`.
"""

import argparse
import dataclasses
import html
import json
import mimetypes
import os
import pathlib
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET

import imagehash
import requests
import yaml
from PIL import Image, ImageOps

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "poster.yml"
_IMAGE_SUFFIXES = (".jpg", ".jpeg")

_XMP_NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
}
for _prefix, _uri in _XMP_NS.items():
    ET.register_namespace(_prefix, _uri)

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XMP_TEMPLATE = """<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="poster.py">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"/>
 </rdf:RDF>
</x:xmpmeta>"""
_XPACKET_BEGIN = '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
_XPACKET_END = '\n<?xpacket end="w"?>\n'

_HASHTAG_RE = re.compile(r'class="mention hashtag"[^>]*>#<span>([^<]+)</span>')
_NON_WORD_RE = re.compile(r"\W")


class PosterError(Exception):
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


def read_json(path: pathlib.Path, default: object = None) -> object:
    try:
        with path.open(encoding="utf-8") as fd:
            return json.load(fd)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def cache_dir(*parts: str) -> pathlib.Path:
    root = os.environ.get("XDG_CACHE_HOME") or pathlib.Path.home() / ".cache"
    path = pathlib.Path(root, "poster", *parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def api_token(name: str) -> str:
    variable = "POSTER_" + _NON_WORD_RE.sub("_", name).upper() + "_API_TOKEN"
    token = os.environ.get(variable, "").strip()
    if not token:
        raise PosterError(f"{variable} is not set: export it with the {name} access token")
    return token


@dataclasses.dataclass
class Attachment:
    id: str
    url: str
    description: str


@dataclasses.dataclass
class Post:
    payload: dict
    url: str
    created_at: str
    tags: list[str]
    attachments: list[Attachment]


class Mastodon:
    """The Mastodon destination: posts a status, and walks the account history."""

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.instance = config["instance"].rstrip("/")
        self.visibility = config.get("visibility", "public")
        self.language = config.get("language")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_token(name)}"
        self.session.headers["User-Agent"] = "poster.py (+https://charlesfleche.net)"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = path if path.startswith("http") else f"{self.instance}{path}"
        response = self.session.request(method, url, timeout=300, **kwargs)
        if not response.ok:
            raise PosterError(f"{method} {url} returned {response.status_code}: {response.text[:500]}")
        return response

    def post(self, image: pathlib.Path, text: str, description: str) -> dict:
        mimetype = mimetypes.guess_type(image.name)[0] or "image/jpeg"
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
                raise PosterError(f"media {media_id} was still processing after {timeout:g}s")
            time.sleep(2)

    def history(self, tag: str | None) -> list[Post]:
        """Every own status with media, newest first, optionally filtered by tag."""
        account = self._request("GET", "/api/v1/accounts/verify_credentials").json()
        url = f"/api/v1/accounts/{account['id']}/statuses"
        params = {"only_media": "true", "exclude_reblogs": "true", "limit": 40}
        posts = []
        while url:
            response = self._request("GET", url, params=params)
            statuses = response.json()
            if not statuses:
                break
            for status in statuses:
                names = {fold(t["name"]) for t in status.get("tags", [])}
                if tag and fold(tag) not in names:
                    continue
                attachments = [
                    Attachment(a["id"], a["url"], a.get("description") or "")
                    for a in status.get("media_attachments", [])
                    if a.get("type") == "image" and a.get("url")
                ]
                if attachments:
                    posts.append(
                        Post(
                            payload=status,
                            url=status["url"],
                            created_at=status["created_at"],
                            tags=self._hashtags(status),
                            attachments=attachments,
                        )
                    )
            url, params = response.links.get("next", {}).get("url"), None
        return posts

    @staticmethod
    def _hashtags(status: dict) -> list[str]:
        """Hashtags with their original casing, which status["tags"] has folded away."""
        found = [html.unescape(t) for t in _HASHTAG_RE.findall(status.get("content", ""))]
        return found or [t["name"] for t in status.get("tags", [])]


_DESTINATION_TYPES = {"mastodon": Mastodon}


@dataclasses.dataclass
class Config:
    path: pathlib.Path
    images: pathlib.Path
    destinations: dict

    @classmethod
    def load(cls, path: pathlib.Path) -> "Config":
        try:
            with path.open(encoding="utf-8") as fd:
                data = yaml.safe_load(fd) or {}
        except FileNotFoundError:
            raise PosterError(f"no configuration file at {path}") from None
        return cls(
            path=path,
            images=(path.parent / data.get("images", ".")).resolve(),
            destinations=data.get("destinations") or {},
        )

    def destination_config(self, name: str) -> dict:
        try:
            return self.destinations[name]
        except KeyError:
            known = ", ".join(sorted(self.destinations)) or "none"
            raise PosterError(f"unknown destination {name!r} in {self.path} (known: {known})") from None

    def destination(self, name: str):
        config = self.destination_config(name)
        try:
            factory = _DESTINATION_TYPES[config["type"]]
        except KeyError:
            known = ", ".join(sorted(_DESTINATION_TYPES))
            raise PosterError(f"destination {name!r} has unsupported type {config.get('type')!r} (known: {known})") from None
        return factory(name, config)

    def images_of(self) -> list[pathlib.Path]:
        if not self.images.is_dir():
            raise PosterError(f"{self.images} is not a directory")
        images = [p for p in self.images.iterdir() if p.suffix.lower() in _IMAGE_SUFFIXES]
        return sorted(images, key=lambda p: p.name)


def payload_path(image: pathlib.Path, destination: str) -> pathlib.Path:
    return image.with_suffix(f".{destination}.json")


def is_posted(image: pathlib.Path, destination: str) -> bool:
    return payload_path(image, destination).exists()


def phash(path: pathlib.Path) -> imagehash.ImageHash:
    with Image.open(path) as img:
        return imagehash.phash(ImageOps.exif_transpose(img))


def local_hashes(images: list[pathlib.Path]) -> dict[pathlib.Path, imagehash.ImageHash]:
    """Perceptual hashes of the local images, cached by size and mtime."""
    cache_path = cache_dir() / "hashes.json"
    cache = read_json(cache_path, {}) or {}
    hashes, stale = {}, []
    for image in images:
        stat = image.stat()
        entry = cache.get(str(image))
        if not entry or entry["size"] != stat.st_size or entry["mtime_ns"] != stat.st_mtime_ns:
            stale.append((image, stat))
        else:
            hashes[image] = imagehash.hex_to_hash(entry["phash"])
    if stale:
        print(f"hashing {len(stale)} local images…", file=sys.stderr)
        for image, stat in stale:
            hashes[image] = phash(image)
            cache[str(image)] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "phash": str(hashes[image]),
            }
        write_json(cache_path, cache)
    return hashes


def download(session: requests.Session, attachment: Attachment, destination: str) -> pathlib.Path:
    suffix = pathlib.PurePosixPath(attachment.url.split("?")[0]).suffix or ".jpg"
    path = cache_dir(destination, "media") / f"{attachment.id}{suffix}"
    if not path.exists():
        response = session.get(attachment.url, timeout=300)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def match(
    local: dict[pathlib.Path, imagehash.ImageHash],
    remote: dict[str, imagehash.ImageHash],
    threshold: int,
) -> tuple[dict[str, tuple[pathlib.Path, int]], dict[str, tuple[pathlib.Path, int]]]:
    """Assign attachments to local images, closest pairs first, one to one."""
    candidates = sorted(
        (local_hash - remote_hash, image.name, image, attachment_id)
        for attachment_id, remote_hash in remote.items()
        for image, local_hash in local.items()
    )
    matched: dict[str, tuple[pathlib.Path, int]] = {}
    nearest: dict[str, tuple[pathlib.Path, int]] = {}
    taken: set[pathlib.Path] = set()
    for distance, _, image, attachment_id in candidates:
        nearest.setdefault(attachment_id, (image, distance))
        if distance <= threshold and attachment_id not in matched and image not in taken:
            matched[attachment_id] = (image, distance)
            taken.add(image)
    unmatched = {k: v for k, v in nearest.items() if k not in matched}
    return matched, unmatched


def cmd_import(args: argparse.Namespace, config: Config) -> None:
    name = args.destination
    destination_config = config.destination_config(name)
    threshold = args.threshold if args.threshold is not None else destination_config.get("match_threshold", 10)
    defaults = {fold(tag) for tag in destination_config.get("default_tags", [])}
    images = config.images_of()
    destination = config.destination(name)

    tag = None if args.all_media else destination_config.get("import_tag")
    posts = destination.history(tag)
    attachments = [(post, attachment) for post in posts for attachment in post.attachments]
    print(f"{len(posts)} posts, {len(attachments)} images on {name}")
    if not attachments:
        return

    downloads = requests.Session()
    remote = {}
    for post, attachment in attachments:
        remote[attachment.id] = phash(download(downloads, attachment, name))
    by_id = {attachment.id: (post, attachment) for post, attachment in attachments}

    matched, unmatched = match(local_hashes(images), remote, threshold)
    payloads = sidecars = 0
    for attachment_id, (image, distance) in sorted(matched.items(), key=lambda kv: kv[1][0].name):
        post, attachment = by_id[attachment_id]
        payload = payload_path(image, name)
        actions = []

        # The payload of an imported post is stored exactly as a post made here
        # would store it, which is what marks the image as posted.
        if payload.exists() and not args.force:
            actions.append("payload kept")
        else:
            actions.append("payload")
            if not args.dry_run:
                write_json(payload, post.payload)
                payloads += 1

        # Every matched image gets its sidecar, so the tags of the posts made
        # before this script are kept under version control too.
        xmp = Xmp.for_image(image)
        existing = xmp.tags
        tags = dedupe(existing + [t for t in post.tags if fold(t) not in defaults])
        description = xmp.description or attachment.description
        if xmp.path.exists() and tags == existing and description == xmp.description:
            actions.append("sidecar kept")
        else:
            actions.append("tags: " + (" ".join(tags) or "(none)"))
            if not args.dry_run:
                xmp.tags = tags
                if description:
                    xmp.description = description
                xmp.save()
                sidecars += 1
        print(f"  {image.name}  d={distance:2d}  {post.url}  [{', '.join(actions)}]")

    for attachment_id, (image, distance) in sorted(unmatched.items(), key=lambda kv: kv[1][1]):
        post, _ = by_id[attachment_id]
        print(f"  UNMATCHED {post.created_at[:10]} {post.url} closest {image.name} d={distance}")

    print(
        f"{len(matched)} matched, {len(unmatched)} unmatched, "
        f"{payloads} payload(s) and {sidecars} sidecar(s) written"
        f"{' (dry run)' if args.dry_run else ''}"
    )


def cmd_post(args: argparse.Namespace, config: Config) -> None:
    name = args.destination
    destination_config = config.destination_config(name)
    images = config.images_of()
    pending = [image for image in images if not is_posted(image, name)]
    if not pending:
        print(f"all {len(images)} images are already posted to {name}")
        return
    image = pending[0]
    xmp = Xmp.for_image(image)
    if not xmp.tags:
        raise PosterError(
            f"{image} has no tags\n"
            f"  tag it with: bin/poster.py tag {image} Tag1 Tag2"
        )
    text = hashtags(destination_config.get("default_tags", []) + xmp.tags)
    description = xmp.description
    print(f"{image.name} ({len(pending)} left)")
    print(f"  {text}")
    if description:
        print(f"  alt: {description}")
    if args.dry_run:
        return
    payload = config.destination(name).post(image, text, description)
    write_json(payload_path(image, name), payload)
    print(f"  posted: {payload.get('url')}")


def cmd_tag(args: argparse.Namespace, config: Config) -> None:
    image = pathlib.Path(args.image)
    if not image.is_file():
        raise PosterError(f"no such image: {image}")
    xmp = Xmp.for_image(image)
    if args.tags:
        xmp.tags = dedupe(args.tags if args.replace else xmp.tags + args.tags)
    if args.description is not None:
        xmp.description = args.description
    if args.tags or args.description is not None:
        xmp.save()
    print(f"{xmp.path.name}: {' '.join(xmp.tags) or '(no tags)'}")
    if xmp.description:
        print(f"  alt: {xmp.description}")


def cmd_list(args: argparse.Namespace, config: Config) -> None:
    name = args.destination
    images = config.images_of()
    pending = [(image, Xmp.for_image(image).tags) for image in images if not is_posted(image, name)]
    if args.untagged:
        pending = [(image, tags) for image, tags in pending if not tags]
    if args.paths:
        # Bare paths, one per line, to pipe into a viewer:
        #   bin/poster.py list mastodon --paths | xargs -d '\n' swayimg
        for image, _ in pending:
            print(image)
        return
    for image, tags in pending:
        print(f"  {image.name}  {' '.join(tags) or 'UNTAGGED'}")
    untagged = sum(1 for _, tags in pending if not tags)
    print(f"{len(images) - len(pending)} posted to {name}, {len(pending)} left, {untagged} untagged")


def main() -> int:
    parser = argparse.ArgumentParser(prog="poster", description=__doc__.splitlines()[0])
    parser.add_argument("-c", "--config", type=pathlib.Path, default=_DEFAULT_CONFIG_PATH)
    subparsers = parser.add_subparsers(required=True)

    post = subparsers.add_parser("post", help="post the next unposted image")
    post.add_argument("destination")
    post.add_argument("-n", "--dry-run", action="store_true")
    post.set_defaults(func=cmd_post)

    tag = subparsers.add_parser("tag", help="read or write the tags of an image")
    tag.add_argument("image")
    tag.add_argument("tags", nargs="*")
    tag.add_argument("-d", "--description", help="alt text")
    tag.add_argument("-r", "--replace", action="store_true", help="replace the tags instead of adding to them")
    tag.set_defaults(func=cmd_tag)

    listing = subparsers.add_parser("list", help="list the images still to post")
    listing.add_argument("destination")
    listing.add_argument("-p", "--paths", action="store_true", help="print bare paths, to pipe into a viewer")
    listing.add_argument("-u", "--untagged", action="store_true", help="only the images without tags")
    listing.set_defaults(func=cmd_list)

    importer = subparsers.add_parser("import", help="import images already posted to the destination")
    importer.add_argument("destination")
    importer.add_argument("-n", "--dry-run", action="store_true")
    importer.add_argument("-t", "--threshold", type=int, help="maximum perceptual hash distance")
    importer.add_argument("--all-media", action="store_true", help="do not filter the history by tag")
    importer.add_argument("-f", "--force", action="store_true", help="overwrite existing payloads")
    importer.set_defaults(func=cmd_import)

    args = parser.parse_args()
    try:
        args.func(args, Config.load(args.config))
    except PosterError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
