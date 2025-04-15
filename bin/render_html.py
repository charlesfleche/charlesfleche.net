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
parser.add_argument("template")
parser.add_argument("data", type=argparse.FileType("r"), default=sys.stdin)
parser.add_argument("output", type=argparse.FileType("w"), default=sys.stdout)
args = parser.parse_args()

data = json.load(args.data)
_ENV.get_template(args.template).stream(**data).dump(args.output)

# data.update(copy.deepcopy(md.Meta))
# data["title"] = data["title"][0]
# data["description"] = data["description"][0]
# data["url"] = f"{data['netloc']}/{data['slug']}"
# data["path"] = f"/{data['slug']}"

# data["meta"].extend(
#     (
#         ("description", data.get("description")),
#         ("og:title", data["title"]),
#         ("og:description", data.get("description")),
#         ("og:type", "article"),
#         ("og:url", data["url"]),
#         ("og:image", ""),
#         ("og:image:alt", ""),
#     )
# )
