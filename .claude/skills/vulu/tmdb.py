"""Finds a movie or a series on TMDB, and its posters at full size.

Usage:
    python3 tmdb.py search movie|tv QUERY [YEAR]
    python3 tmdb.py posters movie|tv ID

search prints one line per result: <id> | <title> | <original title> |
<date> | <TMDB page> | <poster URL>, the poster being TMDB's default one.
posters prints the other posters of a result, the most voted first:
<language> | <width>x<height> | <votes> | <poster URL>.

The TMDB website refuses scripts, but not its API: it reads the API Read
Access Token of https://www.themoviedb.org/settings/api from TMDB_API_TOKEN.
The poster URLs, on image.tmdb.org, need no token.
"""

import json
import os
import sys
import urllib.parse
import urllib.request

_API = "https://api.themoviedb.org/3"
_IMAGE = "https://image.tmdb.org/t/p/original"


def get(path: str, **params: str) -> dict:
    request = urllib.request.Request(
        f"{_API}{path}?" + urllib.parse.urlencode(params),
        headers={"Authorization": f"Bearer {os.environ['TMDB_API_TOKEN']}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def poster(path: str | None) -> str:
    return f"{_IMAGE}{path}" if path else "no poster"


command, kind = sys.argv[1], sys.argv[2]
if kind not in ("movie", "tv"):
    raise SystemExit(f"kind must be movie or tv, not {kind}")

if command == "search":
    params = {"query": sys.argv[3]}
    if len(sys.argv) > 4:
        params["year" if kind == "movie" else "first_air_date_year"] = sys.argv[4]
    results = get(f"/search/{kind}", **params)["results"]
    if not results:
        raise SystemExit(f"no {kind} found for {params}")
    for result in results:
        title, original = (result["title"], result["original_title"]) if kind == "movie" else (result["name"], result["original_name"])
        date = result["release_date"] if kind == "movie" else result["first_air_date"]
        print(
            result["id"],
            title,
            original,
            date or "no date",
            f"https://www.themoviedb.org/{kind}/{result['id']}",
            poster(result["poster_path"]),
            sep=" | ",
        )
elif command == "posters":
    posters = get(f"/{kind}/{sys.argv[3]}/images")["posters"]
    if not posters:
        raise SystemExit(f"{kind} {sys.argv[3]} has no poster")
    for image in sorted(posters, key=lambda image: image["vote_count"], reverse=True):
        print(
            image["iso_639_1"] or "no text",
            f"{image['width']}x{image['height']}",
            image["vote_count"],
            poster(image["file_path"]),
            sep=" | ",
        )
else:
    raise SystemExit(f"command must be search or posters, not {command}")
