import argparse
import json
import sys

parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="+", type=argparse.FileType("r"))
args = parser.parse_args()

data = sorted([json.load(fp) for fp in args.paths], lambda d: d["date"])

json.dump(data, sys.stdout, indent=2, sort_keys=True)
