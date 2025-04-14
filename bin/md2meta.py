import argparse
import copy
import json
from pathlib import Path

import jinja2
import markdown

_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).parent.parent / "templates/ninja"),
    autoescape=jinja2.select_autoescape(),
)

parser = argparse.ArgumentParser()

# input
parser.add_argument("md", type=Path)

# outputs
parser.add_argument("content", type=Path)
parser.add_argument("data", type=argparse.FileType("w"))
parser.add_argument("ninja", type=argparse.FileType("w"))

args = parser.parse_args()

md = markdown.Markdown(extensions=["meta"])
args.content.write_text(md.convert(args.md.read_text()))

data = copy.deepcopy(md.Meta)
for key, value in data.items():
    if len(value) == 1:
        data[key] = value[0]
data["content_path"] = str(args.content)
json.dump(data, args.data, indent=2, sort_keys=True)

_ENV.get_template("step2.ninja.j2").stream(
    template=data.get("template"),
).dump(args.ninja)

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
