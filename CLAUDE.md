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

# Publish: rebuild, prune build/dist of files the graph no longer produces,
# then rsync --delete it to the production host over ssh, forcing IPv4
bin/publish.sh

# Scaffold a new content file
python bin/newcontent.py "My Post Title"                       # content/article/<date>-<slug>/en.md
python bin/newcontent.py "My Post" --category til --lang fr    # content/til/<date>-<slug>/fr.md
python bin/newcontent.py "My Post" --draft                     # content/draft/<date>-<slug>/en.md
```

`mkbuild.py` must be re-run (not just `ninja`) whenever content files are added/removed/renamed, or a Markdown file is edited, since it's what discovers `content/*/*/*.md`, converts the Markdown and regenerates the ninja graph. Running `ninja -C build` alone only re-executes existing build edges. Page edges list `render_html.py` and every theme template as implicit dependencies, and the combine edge lists `global.yml` and its script, so ninja alone picks up changes to those. `build.ninja` itself is a `generator` edge depending on `mkbuild.py`, the stylesheets and their directory (whose mtime changes when one is added, removed or renamed): when one changes, ninja reruns `mkbuild.py` before building. ninja never deletes outputs of removed edges: `build/dist` can hold stale files, which `publish.sh` prunes (files not listed by `ninja -t targets all`, compared relative to `build/dist`; it aborts rather than prune more than half the site).

Dependencies are in `requirements.txt` (installed in `.venv`); `magick` (ImageMagick) and `ninja` must be available on `$PATH` as system binaries.

There is no test suite, linter config, or CI in this repo.

## Content model

Content lives at `content/<category>/[<date>-]<slug>/<lang>.md`, matched by this regex in `bin/mkbuild.py`:

```
.*?/(?P<category>\w+)/((?P<date>\d{4}-\d{2}-\d{2})-)?(?P<slug>[a-z0-9-]+)/(?P<lang>fr|en).md$
```

- **category**: `article`, `til`, `page`, or `draft` (drafts live under `content/draft/<date>-<slug>/` and get titled `DRAFT: ...`; they're still built and published, with `<meta name="robots" content="noindex">` and left out of the sitemap; a deeper `content/draft/<category>/<slug>/` is *not* matched by the `*/*/*.md` glob, and is never built).
- **date** is optional in the folder name; pages like `content/page/index` and `content/page/feed` have none and default to `2009-10-14`.
- **lang** must be `fr` or `en` — this is a per-file suffix, not a directory split; a post can exist in one or both languages as siblings (`en.md`, `fr.md`) in the same slug folder.
- Each `.md` file has a YAML-ish header parsed via the Python-Markdown `meta` extension (`Title:`, `Description:`, `Tags:`, `Template:`, `Path:`, `Robots:`, `og_image:`, one value per line), followed by the Markdown body. `Robots: noindex` keeps a page out of search engines and the sitemap (used by the 404 page).
- `category: page` is written to `/<slug>.html`; everything else to `/<slug>/index.html` — unless the meta header overrides with an explicit `Path:` (used by `content/page/feed` → `/feeds/all.atom.xml`, `content/page/sitemap` → `/sitemap.xml`, `content/page/404` → `/404.html`, `content/page/webmanifest` → `/site.webmanifest`, `content/page/til` → `/til/index.html`). That file path is `fs_path`; `path`, the URL used in links, is `fs_path` without a trailing `index.html` (`/velo-gaspesie/`, `/til/`, `/`), so links never hit the server's trailing-slash redirect. Feed entry IDs (`article_id`) are built from `path` without its trailing slash and must stay stable, or feed readers show old entries as new.
- Sibling files next to `<lang>.md` (images, `src/`, `code/`) are the article's own asset directory; images referenced from Markdown are located relative to the `.md` file, but emitted as root-relative URLs (`/<slug>/...`) so the HTML also works when aggregated in `/til/` and the feed.

Site-wide config (nav links, `<head>` entries, author/site metadata such as `site_title`, the blog's name, default template) lives in `global.yml` and is merged into every article's data by `bin/combine_all_articles_data.py`.

## Build pipeline (how a `.md` becomes a page)

1. **`bin/mkbuild.py`** walks `content/*/*/*.md`. For each file it:
   - Runs Python-Markdown over it with `codehilite`, `fenced_code`, `meta`, and a custom `MdExtension` (see below), whose `HeadingProcessor` shifts headings (with `baselevel=2`: Markdown `#` headings become `<h2>`, the page title being the only `<h1>`; a heading deeper than `<h6>` fails the build), producing an HTML fragment written to `build/<slug>/<lang>.html`. TILs are converted a second time into `build/<slug>/<lang>.nested.html` (`nested_content_path`), with headings starting at `<h3>`, for their aggregation in `/til/`.
   - Writes the parsed metadata + path info as `build/<slug>/<lang>.json`.
   - Emits a per-article `build/<slug>/build.ninja` (from `templates/ninja/article-build.ninja.j2`) with ninja rules for rendering the final page and processing any images/videos found in the content.
   - Also emits `build/static.ninja` to hardlink/copy everything under `templates/theme/static/` into `build/dist/` as-is (favicon, robots.txt, etc.), except stylesheets: `templates/theme/static/css/*.css` are concatenated, in the order of their names (which start with a number, `01-style.css`: the cascade order), into `css/site.<hash>.css`, the hash being the first 8 hex digits of the SHA-256 of the concatenation. Its URL goes to `build/stylesheets.json`, which the combine step passes to the templates as `stylesheets`. The server caches it forever: a changed stylesheet must change URL.
   - Finally emits the root `build/build.ninja` (from `templates/ninja/main-build.ninja.j2`), which `subninja`s every per-article file and adds one edge that combines *all* article JSON + `global.yml` into `build/all_articles_data.json`.
2. **`ninja -C build`** executes that graph:
   - `combine_all_articles_data` (→ `bin/combine_all_articles_data.py`) merges every article's JSON with `global.yml`, computes `url`/`article_id`/`<head>` tags (description, canonical, OpenGraph, robots)/`indexed`/RSS ordering, injects the Home/Mnémographe/#TIL/Rss nav items, and writes the single `build/all_articles_data.json` that every page render reads from.
   - `render_html` (→ `bin/render_html.py`) looks up one article's data by slug inside `all_articles_data.json` and renders it with its declared Jinja `Template` (from `templates/theme/templates/`), with the *entire* `all_articles_data.json` also passed in as `articles` — this is how `index.html.j2` and `til.html.j2` list/aggregate other articles, and how `feed.atom.j2` and `sitemap.xml.j2` build the Atom feed and the sitemap. Templates are autoescaped; `read_text` returns the Markdown fragments as `Markup`, unescaped.
   - `convert_img` shells out to ImageMagick (`magick ... -auto-orient -resize '<geometry>>'`) to produce `.avif`/`.webp`/`.jpeg` variants at fixed widths (`_CONVERT_WIDTHS`: 480/720/960 by default, 160/240/320 in galleries), never upscaling: widths above the image's own are skipped, the largest always exists. EXIF metadata is deliberately kept.
   - `ln` hardlinks (falls back to copy) static files/videos into `build/dist/` unmodified.

Everything lands under `build/dist/`, which is the document root served by `bin/serve.sh` and synced by `bin/publish.sh`.

### The `MediaProcessor` Markdown extension

`bin/mkbuild.py` registers a custom `Treeprocessor` that runs after Markdown's image processor:
- Any `<ul>` whose every item is a lone `<img>` (also wrapped in `<p>`, in loose lists) becomes a `<section class="gallery">` (i.e. write a Markdown bullet list of images to get a gallery, with smaller variants: see `_CONVERT_WIDTHS`).
- Every `<img>` becomes an `<a href="original"><picture>` with AVIF/WebP/JPEG `<source>`s, each a `srcset` of widths with `sizes` (`_DISPLAY_SIZES`, to keep in sync with the layout of `03-main.css`), and every `<video>`-typed `src` becomes a native `<video controls preload="metadata">`. The inner `<img>` gets `width`/`height` (read with Pillow, scaled like ImageMagick does), `decoding="async"`, and `loading="lazy"` except for the page's first media (first three when in a gallery: its first row). Its `alt` is the Markdown alt, unless empty or the `alt text` placeholder: then the image's XMP sidecar `dc:description` (x-default first; a malformed sidecar fails the build), then the Markdown title. Without any, the wrapping `<a>` gets an `aria-label` ("Full size image <file>", in the page's language). Videos get the description as `aria-label`.
- This is also where the ninja build edges for image/video conversion get collected (`self.srcs`), later written into that article's `article-build.ninja.j2`.

## Templates

- `templates/theme/templates/*.j2` — page templates (`base.html.j2` is the shared shell with nav/head/footer; `article.html.j2`, `index.html.j2`, `til.html.j2`, `404.html.j2` extend it; `feed.atom.j2` and `sitemap.xml.j2` are standalone XML, `site.webmanifest.j2` JSON). Selected per-article via the `Template:` meta field or `global.yml`'s default (`article.html.j2`).
- `templates/theme/static/` — copied verbatim to `build/dist/` (icons, `robots.txt`, etc.), stylesheets concatenated into one hashed file.
- `templates/ninja/*.ninja.j2` — the ninja-file generators described above.
- `templates/content/content.md.j2` — the skeleton `bin/newcontent.py` fills in for new posts.

## Other scripts

- `bin/poster.py` — posts the next unposted image of `content/page/2022-01-01-mnemographe` to a destination (Mastodon for now), configured in `poster.yml`. Tags and alt text live in per-image XMP sidecars (`<stem>.xmp`, `dc:subject`/`dc:description`); the REST payload of a post is written next to the image as `<stem>.<destination>.json`, which is what marks it as posted. Access tokens come from `POSTER_<DESTINATION>_API_TOKEN` only. Single file with a uv script header (`bin/poster.py list|tag|post|import`); not part of the site build.
- `bin/instapublish.py` — half-finished helper (uses `instagrapi`) for cross-posting `content/page/2022-01-01-mnemographe` photos to Instagram; not part of the site build.
