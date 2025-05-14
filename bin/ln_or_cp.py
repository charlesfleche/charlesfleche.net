import argparse
import pathlib
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("src", type=pathlib.Path)
parser.add_argument("dst", type=pathlib.Path)
args = parser.parse_args()

args.dst.parent.mkdir(parents=True, exist_ok=True)
args.dst.unlink(missing_ok=True)
try:
    args.dst.hardlink_to(args.src)
except NotImplementedError:
    shutil.copy2(args.src, args.dst)
