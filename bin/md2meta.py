import argparse
import copy
import json
import pathlib

import markdown
import yaml

parser = argparse.ArgumentParser()
parser.add_argument("global_data", type=argparse.FileType("r"))
parser.add_argument("local_data", type=argparse.FileType("r"))
parser.add_argument("md", type=pathlib.Path)
parser.add_argument("data", type=argparse.FileType("w"))

args = parser.parse_args()

data = yaml.safe_load(args.global_data)
data.update(json.load(args.local_data))

md = markdown.Markdown(extensions=["meta"])
data["content"] = md.convert(args.md.read_text())

data.update(copy.deepcopy(md.Meta))
data["title"] = data["title"][0]
data["description"] = data["description"][0]
data["url"] = f"{data['netloc']}/{data['slug']}"
data["path"] = f"/{data['slug']}"

data["meta"].extend(
    (
        ("description", data.get("description")),
        ("og:title", data["title"]),
        ("og:description", data.get("description")),
        ("og:type", "article"),
        ("og:url", data["url"]),
        ("og:image", ""),
        ("og:image:alt", ""),
    )
)

json.dump(data, args.data, indent=2, sort_keys=True)
