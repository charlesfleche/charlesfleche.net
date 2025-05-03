import argparse
import json
import sys

import yaml

raise RuntimeError("Not used")

parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

data = {}
for fp in args.paths:
    data.update(yaml.safe_load(fp))


data["url"] = f"{data['netloc']}{data['path']}"
data["meta"].extend(
    (
        ("description", data["description"]),
        ("og:title", data["title"]),
        ("og:description", data["description"]),
        ("og:type", "article"),
        ("og:url", data["url"]),
        ("og:image", ""),
        ("og:image:alt", ""),
    )
)

json.dump(data, sys.stdout, indent=2, sort_keys=True)
