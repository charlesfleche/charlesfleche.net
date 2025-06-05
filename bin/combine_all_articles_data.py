import argparse
import copy
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("global_data", type=argparse.FileType("r"))
parser.add_argument("out", type=argparse.FileType("w"))
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

global_data = yaml.safe_load(args.global_data)

all_articles_data = {"by_slug": {}}
for fp in args.paths:
    article_data = copy.deepcopy(global_data)
    article_data.update(json.load(fp))

    # URL and ID

    article_data["site_url"] = f"{article_data['netloc']}/"

    article_data["url"] = f"{article_data['netloc']}{article_data['path']}"

    date = datetime.fromisoformat(article_data["date"])
    url = urlparse(article_data["url"])

    article_data["article_id"] = (
        f"tag:{url.netloc},{date.strftime('%Y-%m-%d')}:{article_data['path']}"
    )

    # Head

    article_data["head"].extend(
        [
            {
                "tag": "meta",
                "attrs": {
                    "property": "description",
                    "content": article_data["description"],
                },
            },
            {
                "tag": "meta",
                "attrs": {
                    "property": "og:title",
                    "content": article_data.get("title", ""),
                },
            },
            {
                "tag": "meta",
                "attrs": {
                    "property": "og:description",
                    "content": article_data.get("description", ""),
                },
            },
            {
                "tag": "meta",
                "attrs": {
                    "property": "og:type",
                    "content": "article",
                },
            },
            {
                "tag": "meta",
                "attrs": {
                    "property": "og:url",
                    "content": article_data["url"],
                },
            },
            {
                "tag": "meta",
                "attrs": {
                    "property": "og:image",
                    "content": "",
                },
            },
            {
                "tag": "meta",
                "attrs": {
                    "property": "og:image:alt",
                    "content": "",
                },
            },
        ]
    )

    # Dates

    article_data["datetime"] = (
        datetime.fromisoformat(article_data["date"]).isoformat() + "Z"
    )

    # Draft

    if article_data["category"] == "draft":
        article_data["title"] = f"DRAFT: {article_data['title']}"

    all_articles_data["by_slug"][article_data["slug"]] = article_data

for article_data in all_articles_data["by_slug"].values():
    article_data["nav"].insert(
        0,
        {
            "name": "#TIL",
            "attrs": {
                "href": str(Path(all_articles_data["by_slug"]["til"]["path"]).parent)
            },
        },
    )
    article_data["nav"].insert(
        0,
        {
            "name": "Mnémographe",
            "attrs": {
                "href": str(
                    Path(all_articles_data["by_slug"]["mnemographe"]["path"]).parent
                )
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
                "title": all_articles_data["by_slug"]["feed"]["title"],
            },
        }
    )

# Set feed date to latest article

latest_article = max(
    all_articles_data["by_slug"].values(),
    key=lambda d: d.get("date", "0"),
)
all_articles_data["by_slug"]["feed"]["date"] = latest_article.get("date")

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


json.dump(all_articles_data, args.out, indent=2, sort_keys=True)
