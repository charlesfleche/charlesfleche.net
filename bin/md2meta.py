import argparse
import copy
import json
import pathlib
import re
import sys

import markdown

parser = argparse.ArgumentParser()
parser.add_argument("input", type=pathlib.Path)
parser.add_argument(
    "output", nargs="?", type=argparse.FileType("w"), default=sys.stdout
)

args = parser.parse_args()

meta = {}

md = markdown.Markdown(extensions=["meta"])
meta["html"] = md.convert(args.input.read_text())

meta.update(copy.deepcopy(md.Meta))
meta["title"] = meta["title"][0]

m = re.match(
    r".*?/(?P<group>\w+)/(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9-]+)/(?P<lang>fr|en).md$",
    str(args.input),
)
meta.update(m.groupdict())

json.dump(meta, args.output, indent=2, sort_keys=True)
