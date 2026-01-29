#!python

import argparse
import json
import os
import pathlib

import instagrapi

parser = argparse.ArgumentParser(
    prog="instapublish"
)
parser.add_argument("-n", "--dry-run", action="store_true")
args = parser.parse_args()
print(args)

root = pathlib.Path(__file__).parent.parent / "content/page/2022-01-01-mnemographe"
db_path = root / "instapublish.json"
with db_path.open() as fd:
    db = json.load(fd)

jpgs = root.glob("*.jpg")
already_published = set([root / key for key in db])
jpgs = set(jpgs) ^ already_published
jpg = min(jpgs)
print("Next file to publish:", jpg)

if not args.dry_run:
    cl = instagrapi.Client()
    print(cl.login(os.environ["INSTAGRAM_USERNAME"], os.environ["INSTAGRAM_PASSWORD"]))
    #media = cl.photo_upload(path=jpg)
    #print(media)


