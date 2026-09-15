# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static site generator for charlesfleche.net (a personal blog), built from scratch as a small Python + Ninja pipeline. There is no framework — `bin/mkbuild.py` is a Python script that *generates* a `build.ninja`, and `ninja` then does the actual work of converting Markdown to HTML, resizing images, and copying static assets.

## Commands

```sh
# Regenerate build/build.ninja from content/ and templates/, then build the site
python bin/mkbuild.py && ninja -C build

# Serve the built site locally
bin/serve.sh          # python -m http.server -d build/dist, http://localhost:8000

# Publish (rsync build/dist to the production host over ssh, forcing IPv4)
bin/publish.sh

# Scaffold a new content file
python bin/newcontent.py "My Post Title"                       # content/article/<date>-<slug>/en.md
python bin/newcontent.py "My Post" --category til --lang fr    # content/til/<date>-<slug>/fr.md
python bin/newcontent.py "My Post" --draft                     # writes under content/draft/ instead
```

`mkbuild.py` must be re-run (not just `ninja`) whenever content files are added/removed/renamed or templates change, since it's what discovers `content/*/*/*.md` and regenerates the ninja graph. Running `ninja -C build` alone only re-executes existing build edges.

Dependencies are in `requirements.txt` (installed in `.venv`); `magick` (ImageMagick) and `ninja` must be available on `$PATH` as system binaries.

There is no test suite, linter config, or CI in this repo.

## Content model

Content lives at `content/<category>/[<date>-]<slug>/<lang>.md`, matched by this regex in `bin/mkbuild.py`:

```
.*?/(?P<category>\w+)/((?P<date>\d{4}-\d{2}-\d{2})-)?(?P<slug>[a-z0-9-]+)/(?P<lang>fr|en).md$
```

- **category**: `article`, `til`, `page`, or `draft` (drafts live under `content/draft/<real-category>/...` and get titled `DRAFT: ...`; they're still built and linked, just marked).
- **date** is optional in the folder name; pages like `content/page/index` and `content/page/feed` have none and default to `2009-10-14`.
- **lang** must be `fr` or `en` — this is a per-file suffix, not a directory split; a post can exist in one or both languages as siblings (`en.md`, `fr.md`) in the same slug folder.
- Each `.md` file has a YAML-ish header parsed via the Python-Markdown `meta` extension (`Title:`, `Description:`, `Tags:`, `Template:`, `Path:`, one value per line), followed by the Markdown body.
- `category: page` gets URL `/<slug>.html`; everything else gets `/<slug>/index.html` — unless the meta header overrides with an explicit `Path:` (used by `content/page/feed` → `/feeds/all.atom.xml`, `content/page/til` → `/til/index.html`).
- Sibling files next to `<lang>.md` (images, `src/`, `code/`) are the article's own asset directory; images referenced from Markdown are located relative to the `.md` file.

Site-wide config (nav links, `<head>` entries, author/site metadata, default template) lives in `global.yml` and is merged into every article's data by `bin/combine_all_articles_data.py`.

## Build pipeline (how a `.md` becomes a page)

1. **`bin/mkbuild.py`** walks `content/*/*/*.md`. For each file it:
   - Runs Python-Markdown over it with `codehilite`, `fenced_code`, `meta`, and a custom `MdExtension` (see below), producing an HTML fragment written to `build/<slug>/<lang>.html`.
   - Writes the parsed metadata + path info as `build/<slug>/<lang>.json`.
   - Emits a per-article `build/<slug>/build.ninja` (from `templates/ninja/article-build.ninja.j2`) with ninja rules for rendering the final page and processing any images/videos found in the content.
   - Also emits `build/static.ninja` to hardlink/copy everything under `templates/theme/static/` into `build/dist/` as-is (CSS, favicon, robots.txt, etc.).
   - Finally emits the root `build/build.ninja` (from `templates/ninja/main-build.ninja.j2`), which `subninja`s every per-article file and adds one edge that combines *all* article JSON + `global.yml` into `build/all_articles_data.json`.
2. **`ninja -C build`** executes that graph:
   - `combine_all_articles_data` (→ `bin/combine_all_articles_data.py`) merges every article's JSON with `global.yml`, computes `url`/`article_id`/OpenGraph `<head>` tags/RSS ordering, injects the Home/Mnémographe/#TIL/Rss nav items, and writes the single `build/all_articles_data.json` that every page render reads from.
   - `render_html` (→ `bin/render_html.py`) looks up one article's data by slug inside `all_articles_data.json` and renders it with its declared Jinja `Template` (from `templates/theme/templates/`), with the *entire* `all_articles_data.json` also passed in as `articles` — this is how `index.html.j2` and `til.html.j2` list/aggregate other articles, and how `feed.atom.j2` builds the Atom feed.
   - `convert_img` shells out to ImageMagick to produce `.avif`/`.webp`/`.jpeg` responsive variants at fixed geometries (`default: 960x`, `gallery: 320x`).
   - `ln` hardlinks (falls back to copy) static files/videos into `build/dist/` unmodified.

Everything lands under `build/dist/`, which is the document root served by `bin/serve.sh` and synced by `bin/publish.sh`.

### The `MediaProcessor` Markdown extension

`bin/mkbuild.py` registers a custom `Treeprocessor` that runs after Markdown's image processor:
- Any `<ul>` whose items are all `<img>` becomes a `<section class="gallery">` (i.e. write a Markdown bullet list of images to get a gallery — see `_CONVERT_GEOMETRY["gallery"]` = `320x` vs. the default `960x`).
- Every `<img>` becomes an `<a href="original"><picture>` with AVIF/WebP/JPEG `<source>`s (lazy-loaded), and every `<video>`-typed `src` becomes a native `<video controls preload="metadata">`.
- This is also where the ninja build edges for image/video conversion get collected (`self.srcs`), later written into that article's `article-build.ninja.j2`.

## Templates

- `templates/theme/templates/*.html.j2` — page templates (`base.html.j2` is the shared shell with nav/head/footer; `article.html.j2`, `index.html.j2`, `til.html.j2`, `feed.atom.j2` extend/use it). Selected per-article via the `Template:` meta field or `global.yml`'s default (`article.html.j2`).
- `templates/theme/static/` — copied verbatim to `build/dist/` (CSS, icons, `robots.txt`, etc.).
- `templates/ninja/*.ninja.j2` — the ninja-file generators described above.
- `templates/content/content.md.j2` — the skeleton `bin/newcontent.py` fills in for new posts.

## Other scripts

- `bin/instapublish.py` — half-finished helper (uses `instagrapi`) for cross-posting `content/page/2022-01-01-mnemographe` photos to Instagram; not part of the site build.
