"""Posts a #VuLu status, with one image and its alt text, to mamot.fr.

Usage, from the root of the charlesfleche.net repository:
    bin/secrets.sh run python3 .claude/skills/vulu/post.py --image FILE --alt TEXT --language fr|en [--dry-run] TEXT

It reads the Mastodon access token from POSTER_MASTODON_API_TOKEN, which
bin/secrets.sh sets. --dry-run prints the status, and posts nothing.
"""

import argparse
import hashlib
import json
import mimetypes
import os
import pathlib
import time
import urllib.request
import uuid

_INSTANCE = "https://mamot.fr"


def request(method: str, path: str, auth: str, body: bytes | None = None, headers: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{_INSTANCE}{path}",
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {auth}", "User-Agent": "vulu (+https://charlesfleche.net)", **(headers or {})},
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.load(response)


def multipart(image: pathlib.Path, description: str) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    mimetype = mimetypes.guess_type(image.name)[0]
    if mimetype is None:
        raise SystemExit(f"unknown image type: {image}")
    body = b"".join(
        [
            f'--{boundary}\r\nContent-Disposition: form-data; name="description"\r\n\r\n'.encode(),
            description.encode(),
            f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{image.name}"\r\n'.encode(),
            f"Content-Type: {mimetype}\r\n\r\n".encode(),
            image.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


parser = argparse.ArgumentParser()
parser.add_argument("--image", type=pathlib.Path, required=True)
parser.add_argument("--alt", required=True)
parser.add_argument("--language", choices=["fr", "en"], required=True)
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("text")
args = parser.parse_args()

if not args.text.startswith("#VuLu #"):
    raise SystemExit(f"a VuLu status starts with '#VuLu #<Type>', not: {args.text!r}")
if not args.alt.strip():
    raise SystemExit("the image needs an alt text")
image_bytes = args.image.read_bytes()

print(f"status ({args.language}):\n{args.text}\n\nimage: {args.image} ({len(image_bytes)} bytes)\nalt: {args.alt}")
if args.dry_run:
    raise SystemExit(0)

auth = os.environ["POSTER_MASTODON_API_TOKEN"]
body, content_type = multipart(args.image, args.alt)
status, media = request("POST", "/api/v2/media", auth, body, {"Content-Type": content_type})
# The server answers 202 to the upload, then 206 to the polls, while it
# processes the image, and 200 once it is ready
deadline = time.monotonic() + 120
while status != 200:
    if time.monotonic() > deadline:
        raise SystemExit(f"media {media['id']} was still processing after 120s")
    time.sleep(2)
    status, media = request("GET", f"/api/v1/media/{media['id']}", auth)

# The same status and image make the same key: Mastodon answers a retry
# within an hour with the first post, and posts nothing new
key = hashlib.sha256(args.text.encode() + image_bytes).hexdigest()
_, posted = request(
    "POST",
    "/api/v1/statuses",
    auth,
    json.dumps({"status": args.text, "media_ids": [media["id"]], "visibility": "public", "language": args.language}).encode(),
    {"Content-Type": "application/json", "Idempotency-Key": f"vulu-{key}"},
)
print(f"\nposted: {posted['url']}")
