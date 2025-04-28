import argparse
import copy
import json
import sys

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("global_data", type=argparse.FileType("r"))
parser.add_argument("out", type=argparse.FileType("w"))
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

global_data = yaml.safe_load(args.global_data)

all_articles_data = {
    "by_slug": {}
}
for fp in args.paths:
    article_data = copy.deepcopy(global_data)
    article_data.update(json.load(fp))

    article_data["url"] = f"{article_data['netloc']}{article_data['path']}"
    article_data["meta"].extend(
        (
            ("description", article_data["description"]),
            ("og:title", article_data["title"]),
            ("og:description", article_data["description"]),
            ("og:type", "article"),
            ("og:url", article_data["url"]),
            ("og:image", ""),
            ("og:image:alt", ""),
        )
    )

    all_articles_data["by_slug"][article_data["slug"]] = article_data

all_articles_data["by_date"] = list(reversed(sorted(
    [article for article in all_articles_data["by_slug"].values() if article["category"] != "page"],
    key=lambda article: article.get("date")
)))

json.dump(all_articles_data, args.out, indent=2, sort_keys=True)
