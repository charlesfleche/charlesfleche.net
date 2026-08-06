# import imagehash
# from PIL import Image

# d = []

# for p, n in (
#     ("20260530-190125.jpg", "A"),
#     ("20260604-175428.jpg", "B"),
#     ("20260523-150759.jpg", "C"),
#     ("6b6633ca9374387f.jpg", "a"),
#     ("87baa63f24857500.jpg", "b"),
#     ("e1b12bce17e5ba66.jpg", "c"),
# ):
#     im = Image.open(f"content/page/2022-01-01-mnemographe/{p}")
#     hsh = imagehash.average_hash(im)
#     d.append((n, hsh))

# for p0, h0 in d:
#     for p1, h1 in d:
#         print(f"{p0} - {p1} : {h0 - h1}")

from pprint import pprint

from mastodon import Mastodon

client = Mastodon(
    access_token="asdcasdcasdcsadc",
    api_base_url="https://mamot.fr",
)
account = client.account_verify_credentials()
pprint(account)
pprint("----")
user_id = account["id"]
statuses = client.account_statuses(user_id, limit=40)

while statuses:
    for status in statuses:
        attachments = status.get("media_attachments", [])
        if not attachments:
            continue

        tags = {tag.get("name", "").lower() for tag in status.get("tags")}
        if "mnémographe" not in tags:
            continue

        for media in attachments:
            if media["type"] != "image":
                continue

        # img_url = media.get("url") or media.get("preview_url")
        pprint(status)
        exit(0)

    statuses = client.fetch_next(statuses)
