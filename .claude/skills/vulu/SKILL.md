---
name: vulu
description: Post a #VuLu status on the user's Mastodon account (@charlesfleche@mamot.fr), with the poster or cover and its alt text. Use when the user asks to post, toot or log a #VuLu, or says they watched, read, played or saw a film, series, book, comic, game or show and want it on Mastodon.
---

# Post a #VuLu

#VuLu ("Vu, Lu": seen, read) is the user's public log, on https://mamot.fr/@charlesfleche, of the works they finish. A post is public as soon as it is sent, and stays in the feeds of its followers even if deleted. Always show the draft and ask before posting.

## Format

The status is one line, and an optional comment as a second paragraph:

```
#VuLu #<Type> <Title> (<year>)[, <author>]

[<comment>]
```

- Write `#VuLu` with this case exactly.
- Use one of these types. Do not add an accent: Mastodon makes `#Serie` and `#Série` the same hashtag, and the user always wrote `#Serie`.

  | Type | For |
  |------|-----|
  | `#Film` | a film |
  | `#Serie` | a series, with the seasons when the user gives them: `Silo (2023) Seasons 1 and 2` |
  | `#Livre` | a book: `Carnets d'Ukraine, Michel Hazanavicius (2025)` |
  | `#BD` | a comic: `Louis Riel, Chester Brown` |
  | `#Joué` | a video game: `Far Cry 5 (2018)` |
  | `#Théâtre` | a play |
  | `#Vu` | a live show, such as a concert or a comedy show |

- Write the title as the user wrote it, and the year of release (the first season for a series). For a book or a comic, write the author after a comma.
- Add a comment only when the user gives one. Use their words, and do not write a review for them.
- Add a place or a person only when the user names one: `#Montréal`, `@davduf`.
- The language of the status is the one of the comment: `fr` or `en`. Without a comment, use `en`, as in the earlier posts.

## The image

Every post has one image: the poster, the cover or a photo.

- For a film or a series, take the poster from TMDB. TMDB refuses scripts on its website, so use its API through the script of this skill. It reads the API Read Access Token from `TMDB_API_TOKEN`, which `bin/secrets.sh run` sets. If the token is missing, ask the user to add it with `bin/secrets.sh edit`, and do not scrape the website.
  ```
  bin/secrets.sh run python3 .claude/skills/vulu/tmdb.py search movie "Jojo Rabbit" 2019
  bin/secrets.sh run python3 .claude/skills/vulu/tmdb.py search tv "Silo"
  bin/secrets.sh run python3 .claude/skills/vulu/tmdb.py posters movie 515001
  ```
  `search` gives the default poster of each result. If several results match, ask the user which one. `posters` lists the other posters, the most voted first. Use the default poster, unless the user asks for another one or its language is not the one of the title (a French title takes a `fr` poster).
- For another type, ask the user for the image: a file or a URL.
- Download the image into the scratchpad, in a new directory: `curl -sf <URL> -o <scratchpad>/vulu/<name>.jpg`.

## The alt text

Look at the image with the Read tool. Write the alt text as one line: the English sentence, ` / `, then its French translation. Name the work, then describe what the image shows, in about 15 to 25 words for each language. Copy the main text of a poster: the title and a tagline, if any.

```
Poster of Jojo Rabbit: a boy in a Hitler Youth uniform, surrounded by the cast, among them a mustached Hitler, on a red background. / Affiche de Jojo Rabbit : un garçon en uniforme des Jeunesses hitlériennes, entouré des acteurs, dont un Hitler moustachu, sur fond rouge.
```

## Procedure

1. Find the work and its year. If the title or the type is not clear, ask.
2. Get the image and write its alt text.
3. Make a dry run, and show its output and the image path to the user:
   ```
   bin/secrets.sh run python3 .claude/skills/vulu/post.py --image <file> --alt "<alt text>" --language en --dry-run "#VuLu #Film Jojo Rabbit (2019)"
   ```
   For a comment, put a blank line in the text: `$'#VuLu #Film Buffet Froid (1979)\n\nC\'était... Étrange !'`.
4. Ask the user to confirm. Post only after a yes, with the same command without `--dry-run`. Give the user the URL of the post that the script prints.

`post.py` reads the Mastodon token from `POSTER_MASTODON_API_TOKEN`, which `bin/secrets.sh run` sets from `secrets.env.age`. Run the scripts only through `bin/secrets.sh run`. Never decrypt `secrets.env.age` yourself, and never print the environment of such a command. If the script fails after the upload, run the same command again within the hour: Mastodon recognizes the same status and image, and does not post twice.
