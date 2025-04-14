import argparse
import json
import sys

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

data = {}
for fp in args.paths:
    data.update(yaml.safe_load(fp))

json.dump(data, sys.stdout, indent=2, sort_keys=True)
