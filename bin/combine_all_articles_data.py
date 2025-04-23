import argparse
import json
import sys

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

data = [yaml.safe_load(fp) for fp in args.paths]
data = [d for d in data if d is not None]
data = sorted(data, key=lambda d: d.get("date", ""))

json.dump(data, sys.stdout, indent=2, sort_keys=True)
