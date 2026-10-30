import argparse
import copy
import json
from collections import defaultdict
from datetime import datetime
from urllib.parse import urljoin, urlparse

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("global_data", type=argparse.FileType("r"))
parser.add_argument("stylesheets", type=argparse.FileType("r"))
parser.add_argument("out", type=argparse.FileType("w"))
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

global_data = yaml.safe_load(args.global_data)
# The stylesheets, as published: concatenated, under a hash of their content
global_data["stylesheets"] = json.load(args.stylesheets)

all_articles_data = {"by_slug": {}}
for fp in args.paths:
    article_data = copy.deepcopy(global_data)
    article_data.update(json.load(fp))

    # URL and ID

    article_data["site_url"] = f"{article_data['netloc']}/"

    article_data["url"] = f"{article_data['netloc']}{article_data['path']}"

    date = datetime.fromisoformat(article_data["date"])
    url = urlparse(article_data["url"])

    # Without the trailing slash, as the IDs were before: an entry whose ID
    # changes shows up as a new one in feed readers
    article_data["article_id"] = (
        f"tag:{url.netloc},{date.strftime('%Y-%m-%d')}:{article_data['path'].rstrip('/')}"
    )

    # Draft

    if article_data["category"] == "draft":
        article_data["title"] = f"DRAFT: {article_data['title']}"

    # Head

    def meta(attr, key, content):
        return {"tag": "meta", "attrs": {attr: key, "content": content}}

    head = article_data["head"]
    head.extend(
        [
            # description is a standard name, not an OpenGraph property
            meta("name", "description", article_data["description"]),
            {"tag": "link", "attrs": {"rel": "canonical", "href": article_data["url"]}},
            meta("property", "og:site_name", article_data["site_title"]),
            meta("property", "og:title", article_data["title"]),
            meta("property", "og:description", article_data["description"]),
            meta(
                "property",
                "og:type",
                "website" if article_data["category"] == "page" else "article",
            ),
            meta("property", "og:url", article_data["url"]),
        ]
    )
    if og_image := article_data.get("og_image"):
        head.extend(
            [
                meta("property", "og:image", urljoin(article_data["url"], og_image)),
                meta("name", "twitter:card", "summary_large_image"),
            ]
        )
    else:
        head.append(meta("name", "twitter:card", "summary"))

    # Drafts are published to be previewed, but must not be indexed, nor
    # pages with a Robots: noindex header (404)
    if article_data["category"] == "draft":
        article_data["robots"] = "noindex"
    article_data["indexed"] = "noindex" not in article_data.get("robots", "")
    if not article_data["indexed"]:
        head.append(meta("name", "robots", article_data["robots"]))

    # Dates

    article_data["datetime"] = (
        datetime.fromisoformat(article_data["date"]).isoformat() + "Z"
    )

    all_articles_data["by_slug"][article_data["slug"]] = article_data

for article_data in all_articles_data["by_slug"].values():
    article_data["nav"].insert(
        0,
        {
            "name": "#TIL",
            "attrs": {
                "href": all_articles_data["by_slug"]["til"]["path"]
            },
        },
    )
    article_data["nav"].insert(
        0,
        {
            "name": "Mnémographe",
            "attrs": {
                "href": all_articles_data["by_slug"]["mnemographe"]["path"]
            },
        },
    )
    article_data["nav"].insert(
        0,
        {
            "name": "Home",
            "attrs": {"href": "/"},
        },
    )
    article_data["nav"].append(
        {
            "name": "Rss",
            "attrs": {"href": all_articles_data["by_slug"]["feed"]["path"]},
        }
    )
    article_data["head"].append(
        {
            "tag": "link",
            "attrs": {
                "href": all_articles_data["by_slug"]["feed"]["path"],
                "type": all_articles_data["by_slug"]["feed"]["type"],
                "rel": "alternate",
                "title": article_data["site_title"],
            },
        }
    )

by_date = []
all_articles_data["by_date"] = by_date

by_category = defaultdict(list)
all_articles_data["by_category"] = by_category

for article_data in reversed(
    sorted(
        all_articles_data["by_slug"].values(),
        key=lambda article: article.get("date"),
    )
):
    category = article_data["category"]

    by_category[category].append(article_data)

    if category not in ("draft", "page"):
        by_date.append(article_data)

# Set feed date to latest published article: drafts and pages are not in the feed

feed_data = all_articles_data["by_slug"]["feed"]
feed_data["date"] = by_date[0]["date"]
feed_data["datetime"] = by_date[0]["datetime"]

json.dump(all_articles_data, args.out, indent=2, sort_keys=True)
