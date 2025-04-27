import argparse
import json
import sys
from pathlib import Path

import jinja2


def read_text(path):
    return Path(path).read_text()


_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        Path(__file__).parent.parent / "templates/theme/templates"
    ),
    autoescape=jinja2.select_autoescape(),
)
_ENV.filters["read_text"] = read_text

parser = argparse.ArgumentParser()
parser.add_argument("slug")
parser.add_argument("data", type=argparse.FileType("r"), default=sys.stdin)
parser.add_argument("html", type=argparse.FileType("w"), default=sys.stdout)
args = parser.parse_args()

all_articles_data = json.load(args.data)

article_data = all_articles_data["by_slug"][args.slug]
_ENV.get_template(
    article_data["template"]
).stream(
    article=article_data,
    all_articles=all_articles_data
).dump(args.html)
