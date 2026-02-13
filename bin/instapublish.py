#!python

import argparse
import contextlib
import json
import os
import pathlib

import instagrapi

_REPO_ROOT = pathlib.Path(__file__).parent.parent
_ARTICLE_ROOT = _REPO_ROOT / "content/page/2022-01-01-mnemographe"
_DB_PATH = _ARTICLE_ROOT / "instapublish.json"
_SESSION_PATH = _REPO_ROOT / ".instagram-session.json"

_CLIENT = instagrapi.Client()

@contextlib.contextmanager
def _db():
    with _DB_PATH.open() as fd:
        db = json.load(fd)
        yield db
    
    with _DB_PATH.open("w") as fd:
        json.dump(db, fp, indent=4, sort_keys=True, ensure_ascii=False)

def login(ns: argparse.Namespace) -> None:
    _CLIENT.login(ns.username, ns.password)
    _CLIENT.dump_settings(_SESSION_PATH)

def publish_next(ns: argparse.Namespace) -> None:
    print("publish_next")

parser = argparse.ArgumentParser(
    prog="instapublish"
)
subparsers = parser.add_subparsers(required=True)

parser_login = subparsers.add_parser("login")
parser_login.add_argument("username")
parser_login.add_argument("password")
parser_login.set_defaults(func=login)

parser_publish = subparsers.add_parser("publish_next")
parser_publish.add_argument("-n", "--dry-run", action="store_true")
parser_publish.set_defaults(func=publish_next)

args = parser.parse_args()
args.func(args)

# root = pathlib.Path(__file__).parent.parent / "content/page/2022-01-01-mnemographe"
# db_path = root / "instapublish.json"
# with db_path.open() as fd:
#     db = json.load(fd)

# jpgs = root.glob("*.jpg")
# already_published = set([root / key for key in db])
# jpgs = set(jpgs) ^ already_published
# jpg = min(jpgs)
# print("Next file to publish:", jpg)

# if not args.dry_run:
#     cl = instagrapi.Client()
#     print(cl.login(os.environ["INSTAGRAM_USERNAME"], os.environ["INSTAGRAM_PASSWORD"]))
#     media = cl.photo_upload(path=jpg)

#     db[jpg.name] = media.dict()
#     with db_path.open("w") as fp:
#         json.dump(db, fp, indent=4, sort_keys=True, ensure_ascii=False)



