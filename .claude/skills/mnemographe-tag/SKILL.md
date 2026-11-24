---
name: mnemographe-tag
description: Tag the mnémographe photos and write their bilingual alt texts, in the user's own style, through mnemographe-tag. Use when the user asks to tag, describe or caption new or untagged mnémographe photos, or to translate or fix their alt texts.
---

# Tag the mnémographe photos

The photos are in `content/page/2022-01-01-mnemographe` of the ingest clone, `~/src/charlesfleche.net-mnemograph-ingest`. Work there, never in `~/src/charlesfleche.net`. Tags and alt texts live in the XMP sidecars, and only `mnemographe-tag` writes them: it commits, pushes and mirrors to the phone. pi then posts the tagged photos on its timers, so a tag set is public within hours.

## Conventions

Tags are one list, base tags first, then places, then subjects. Every word comes in English and French, English first: `Snow Neige`, `Bridge Pont`. A word that is the same in both languages comes once: `Graffiti`, `Train`, `Concert`. Proper nouns come once: `Qwirkle`, `LeonardCohen`. Tags are CamelCase, without spaces.

- Base tags:
  - Black and white, before 2026-03-20: `BlackAndWhite Photographie NoirEtBlanc`.
  - Black and white, from 2026-03-20: `Monochrome Monochrom BlackAndWhite Photographie NoirEtBlanc`.
  - Color: `Photography Photographie`, and no black-and-white or Monochrome tag.
- Places, from the GPS position of the photo:
  - Before 2026: `Canada Québec Montréal`, `France Cambrai`, `France Paris`, `Spain Espagne Valencia Valence`, `USA ÉtatsUnis SanFrancisco`.
  - From 2026: the same without `Canada`, for example `Québec Montréal`.
  - Name a city or a park only when the position is clear. Without GPS, give a place only when the photo shows it, and no place otherwise.
- Two tags that differ only by an accent are refused, because they make the same hashtag. Keep the French form only: `Néon`, `Détour`, `Cinéma`, `Téléphone`.
- The alt text is one line: the English sentence, ` / `, then its French translation. For example: `A bumblebee on a pink coneflower. / Un bourdon sur une échinacée rose.` Describe what is visible, in a neutral register, in about 10 to 15 words. Do not start with "A photo of".
- The page is in English.

## Procedure

1. Find the photos without a sidecar, or with an empty tag or alt text:
   ```
   cd ~/src/charlesfleche.net-mnemograph-ingest && git pull --rebase
   cd content/page/2022-01-01-mnemographe
   for f in *.jpg *.jpeg; do [ -e "${f%.*}.xmp" ] || echo "$f"; done
   ```
2. Read their GPS position and camera: `exiftool -T -n -filename -Model -GPSLatitude -GPSLongitude <files>`.
3. Find the color photos by their mean saturation. Above 0.05 is color:
   `magick <file> -resize 160x -colorspace HSL -channel G -separate +channel -format '%[fx:mean]' info:`
4. Look at the photos on contact sheets of 16, labeled with a number and the stem. Put them in the scratchpad, then read each sheet:
   `magick montage -label '<n> <stem>' <file> ... -tile 4x4 -geometry 300x300+4+4 -pointsize 18 sheet01.jpg`
   The site build has small copies in `build/dist/mnemographe/<stem>.320x.jpeg`. If they are missing, use the originals.
5. Write two files in the scratchpad:
   - `tags.txt`, one line per photo: `<stem> <tag> <tag> ...`, base tags included.
   - `alts.txt`, one line per photo: `<file name>|<English> / <French>`.
6. Show the user the list, and ask before you apply it. Flag the guesses: places without GPS, and subjects you are not sure of.
7. Apply it with `mnemographe-tag`, with the script of this skill as the editor:
   ```
   GIT_EDITOR="python3 ~/src/charlesfleche.net/.claude/skills/mnemographe-tag/apply.py <scratchpad>/tags.txt <scratchpad>/alts.txt" mnemographe-tag
   ```
   The script only fills empty tags and empty alt texts. It stops, and writes nothing, if a photo already has one, or if a photo of the files is not in the editor.
8. Check the result. Every listed sidecar must have tags and an alt text: `exiftool -s3 -XMP-dc:Subject -XMP-dc:Description <stem>.xmp`.

## Pitfalls

- If the user has `mnemographe-tag` open at the same time, the tool refuses to save the session that saves second. That is expected: run it again.
- `mnemographe-tag` does not publish the blog. The alt texts reach the site at the next ingest, or with `uv run bin/publish.sh` in the ingest clone, when the user asks for it.
- Never write the sidecars by hand, and never commit in the ingest clone yourself.
