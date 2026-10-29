#!/usr/bin/env python3

import hashlib
import json
import mimetypes
import pathlib
import re
from contextlib import contextmanager
from xml.etree import ElementTree as ET

import jinja2
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from PIL import Image

_REPO_DIR = pathlib.Path(__file__).parent.parent.absolute()
_BIN_DIR = _REPO_DIR / "bin"
_BUILD_DIR = _REPO_DIR / "build"
_DIST_DIR = _BUILD_DIR / "dist"
_CONTENT_DIR = _REPO_DIR / "content"
_NINJA_TEMPLATES_DIR = _REPO_DIR / "templates/ninja"
_THEME_DIR = _REPO_DIR / "templates/theme"
_THEME_STATIC_DIR = _THEME_DIR / "static"
_STYLESHEETS_DIR = _THEME_STATIC_DIR / "css"
_GLOBAL_DATA_PATH = _REPO_DIR / "global.yml"
_STYLESHEETS_PATH = _BUILD_DIR / "stylesheets.json"

_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_NINJA_TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(),
)


def safe_ninja(path):
    path = pathlib.PurePosixPath(path)
    return re.sub(r"[:$]", r"$\g<0>", str(path))


_ENV.filters["safe_ninja"] = safe_ninja


# Pages are rendered by this script, with any of these templates
_RENDER_HTML_DEPS = [
    safe_ninja(path)
    for path in [_BIN_DIR / "render_html.py", *sorted((_THEME_DIR / "templates").iterdir())]
]

_SUBNINJA_PATHS = []
_ARTICLES_DATA_PATHS = []

_CONVERT_GEOMETRY = {"default": "960x", "gallery": "320x"}

# Placeholder alt of many images, not a description
_PLACEHOLDER_ALT = "alt text"

_XMP_NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Accessible name of a link to a full size image that has no description
_FULL_SIZE_LABEL = {"en": "Full size image", "fr": "Image en taille réelle"}

# EXIF orientations of images rotated by a quarter turn
_EXIF_ORIENTATION = 0x0112
_EXIF_TRANSPOSED = (5, 6, 7, 8)


def _xmp_description(image_path):
    """dc:description of the image's XMP sidecar, as written by poster.py"""
    xmp_path = image_path.with_suffix(".xmp")
    if not xmp_path.is_file():
        return ""
    root = ET.parse(xmp_path).getroot()
    for description in root.iter(f"{{{_XMP_NS['rdf']}}}Description"):
        # Shorthand form: dc:description as an attribute
        if value := description.get(f"{{{_XMP_NS['dc']}}}description"):
            return value
        element = description.find("dc:description", _XMP_NS)
        if element is not None:
            # Usually a rdf:Alt of localized rdf:li: the x-default one first,
            # as poster.py reads it
            lis = element.findall(".//rdf:li", _XMP_NS)
            lis.sort(key=lambda li: li.get(_XML_LANG) != "x-default")
            for candidate in [*lis, element]:
                if text := (candidate.text or "").strip():
                    return text
    return ""


def _display_size(image_path, geometry):
    """Size of the image once oriented and resized to geometry (\"960x>\")"""
    with Image.open(image_path) as image:
        width, height = image.size
        if image.getexif().get(_EXIF_ORIENTATION) in _EXIF_TRANSPOSED:
            width, height = height, width
    max_width = int(geometry.rstrip("x>"))
    if width > max_width:
        # Rounding half up, as ImageMagick does
        width, height = max_width, int(height * max_width / width + 0.5)
    return width, height


def _article_data(md_path, meta):
    """Article data from its markdown path and meta headers"""
    data = {}
    for key, value in meta.items():
        if len(value) == 1:
            data[key] = value[0]

    # Extracting article data from path

    m = re.match(
        r".*?/(?P<category>\w+)/((?P<date>\d{4}-\d{2}-\d{2})-)?(?P<slug>[a-z0-9-]+)/(?P<lang>fr|en).md$",
        str(pathlib.PurePosixPath(md_path)),
    )
    if m is None:
        raise RuntimeError(f"Failed to parse {md_path}")
    data.update(m.groupdict())

    if data["date"] is None:
        data["date"] = "2009-10-14"

    if data["category"] == "page":
        data["fs_path"] = data.get("path", f"/{data['slug']}.html")
    else:
        data["fs_path"] = f"{data.get('path', '/' + data['slug']).rstrip('/')}/index.html"

    # URL path, as served: directories end with a slash, else the server redirects
    data["path"] = re.sub(r"(?<=/)index\.html$", "", data["fs_path"])

    return data


@contextmanager
def _mkdir_open(path, *args, **kwargs):
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open(*args, **kwargs) as fp:
        yield fp


def _render(fp, template_name, *args, **kwargs):
    _ENV.get_template(template_name).stream(*args, **kwargs).dump(fp)


def _add_subninja(path):
    _SUBNINJA_PATHS.append(path.relative_to(_BUILD_DIR))


def _add_article_data_path(path):
    _ARTICLES_DATA_PATHS.append(path)


class MediaProcessor(Treeprocessor):
    def __init__(self, md, md_path):
        super().__init__(md)

        self.md_path = md_path
        # Images are located relative to the markdown file
        self.base_dir = md_path.parent
        self.srcs = []
        self.media_count = 0

    def _url(self, path):
        """URL of a media, absolute: the content is also aggregated in other pages (TIL, feed)"""
        return f"{self.url_dir}/{path}"

    def run(self, root):
        # The meta preprocessor already ran: the article's Path: is known
        data = _article_data(self.md_path, self.md.Meta)
        fs_path = data["fs_path"]
        self.lang = data["lang"]
        self.url_dir = str(pathlib.PurePosixPath(fs_path).parent).rstrip("/")

        self._make_galleries(root)
        self._imgs_to_media(root)

    def _make_galleries(self, root):
        for ul in list(root.iter("ul")):
            # Only lists of images: each item holding one image and no text
            img_els = [self._lone_img(li) for li in ul]
            if not img_els or None in img_els:
                continue

            ul.clear()
            ul.tag = "section"
            ul.attrib["class"] = "gallery"
            for img in img_els:
                img.attrib["__purpose"] = "gallery"
                ul.append(img)

    @staticmethod
    def _lone_img(li):
        """The img that is li's only content, <li><img></li> or <li><p><img></p></li> in loose lists"""
        imgs = li.findall(".//img")
        if (
            len(imgs) == 1
            and {el.tag for el in li.iter()} <= {"li", "p", "img"}
            and not "".join(li.itertext()).strip()
        ):
            return imgs[0]
        return None

    def _imgs_to_media(self, root):
        # Buffering all imgs so img generated by picture
        # are not iterated
        img_els = list(root.iter("img"))
        for element in img_els:
            src = element.attrib.get("src", "")
            if m := re.match(r"^(image|video)/.*$", mimetypes.guess_type(src)[0] or ""):
                typ = m.groups()[0]
                self._GENERATOR_BY_MEDIA_TYPE[typ](self, element)
                self.media_count += 1

    def _to_picture(self, el):
        el.tag = "a"

        src = pathlib.Path(el.attrib.pop("src"))

        # The alt belongs to the img, not the link
        alt, title = self._description(el, src)

        el.attrib["href"] = self._url(src)
        if not alt:
            # The picture is the link's only content: without alt, the link
            # would have no name for screen readers
            el.set("aria-label", f"{_FULL_SIZE_LABEL[self.lang]} {src.name}")

        self.srcs.append(["ln", safe_ninja(src), safe_ninja(src), {}])

        geometry = _CONVERT_GEOMETRY[el.attrib.pop("__purpose", "default")]
        args = {
            "geometry": geometry,
        }

        picture = ET.SubElement(el, "picture")
        # Hardcoding mimetype rather than calling mimetypes.guess_type
        # some older versions of guess_type do not recognize webp
        for suffix, mimetype in [
            (".avif", "image/avif"),
            (".webp", "image/webp"),
            (".jpeg", "image/jpeg"),
        ]:
            dst = pathlib.Path(src.with_suffix(f".{geometry}{suffix}").name)

            source = ET.SubElement(picture, "source")
            source.set("srcset", self._url(dst))
            source.set("type", mimetype)

            self.srcs.append(["convert_img", safe_ninja(src), safe_ninja(dst), args])

        width, height = _display_size(self.base_dir / src, geometry)

        img = ET.SubElement(picture, "img")
        img.set("src", self._url(dst))
        img.set("alt", alt)
        if title:
            img.set("title", title)
        # Reserves the image's space before it loads: no layout shift
        img.set("width", str(width))
        img.set("height", str(height))
        # The first media is likely the largest paint of the page: not deferred
        if self.media_count:
            img.set("loading", "lazy")
        img.set("decoding", "async")

    def _description(self, el, src):
        """Alt and title of a media, popped from its element"""
        alt = el.attrib.pop("alt", "")
        title = el.attrib.pop("title", "")
        if not alt or alt == _PLACEHOLDER_ALT:
            alt = _xmp_description(self.base_dir / src) or title
        return alt, title

    def _to_video(self, el):
        el.tag = "video"

        src = pathlib.Path(el.attrib.pop("src"))
        # Videos are not resized for galleries
        el.attrib.pop("__purpose", None)

        # alt is not a video attribute: the description is its accessible name
        alt, title = self._description(el, src)
        if alt:
            el.set("aria-label", alt)
        if title:
            el.set("title", title)

        el.set("controls", "")
        el.set("preload", "metadata")

        source = ET.SubElement(el, "source")
        source.set("src", self._url(src))
        source.set("type", mimetypes.guess_type(str(src))[0])

        self.srcs.append(["ln", safe_ninja(src), safe_ninja(src), {}])

    _GENERATOR_BY_MEDIA_TYPE = {
        "image": _to_picture,
        "video": _to_video,
    }


class HeadingProcessor(Treeprocessor):
    """Shifts headings: "#" is an h<baselevel>, "##" the level below, etc."""

    def __init__(self, md, baselevel):
        super().__init__(md)

        self.baselevel = baselevel

    def run(self, root):
        for el in root.iter():
            if m := re.fullmatch(r"h([1-6])", el.tag):
                level = int(m[1]) + self.baselevel - 1
                if level > 6:
                    raise RuntimeError(f"Heading too deep, h{level}: {el.text}")
                el.tag = f"h{level}"


class MdExtension(Extension):
    def __init__(self, md_path, baselevel, **kwargs):
        super().__init__(**kwargs)

        self.md_path = md_path
        self.baselevel = baselevel

    def extendMarkdown(self, md):
        md.treeprocessors.register(
            HeadingProcessor(md, self.baselevel), "headingprocessor", 20
        )
        md.MediaProcessor = MediaProcessor(md, self.md_path)
        md.treeprocessors.register(
            md.MediaProcessor,
            "mediaprocessor",
            20,  # <= 20 to run after img processor
        )


def _hashed(path):
    """03-main.css -> 03-main.<hash of its content>.css: a new URL whenever it
    changes, so browsers can cache it forever"""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    return path.with_suffix(f".{digest}{path.suffix}")


# Stylesheets, in cascade order: the order of their file names, which start
# with a number

stylesheet_srcs = sorted(_STYLESHEETS_DIR.glob("*.css"))

with _mkdir_open(_STYLESHEETS_PATH, "w") as fp:
    json.dump(
        [f"/{_hashed(src).relative_to(_THEME_STATIC_DIR).as_posix()}" for src in stylesheet_srcs],
        fp,
    )

# Copy static theme

static_paths = []
for src in sorted(_THEME_STATIC_DIR.glob("**/*")):
    if not src.is_file():
        continue
    dst = _hashed(src) if src in stylesheet_srcs else src
    static_paths.append(
        (safe_ninja(src), safe_ninja(_DIST_DIR / dst.relative_to(_THEME_STATIC_DIR)))
    )

static_build_path = _BUILD_DIR / "static.ninja"
with _mkdir_open(static_build_path, "w") as fp:
    _render(fp, "static-build.ninja.j2", static_paths=static_paths)
_add_subninja(static_build_path)

# Make articles build.ninja

def _markdown(md_path, baselevel):
    return markdown.Markdown(
        extensions=[
            "codehilite",
            "meta",
            "fenced_code",
            MdExtension(md_path, baselevel),
        ]
    )


for md_path in _CONTENT_DIR.glob("*/*/*.md"):
    # Parsing article's markdown

    # The page title is the only h1: content "#" headings are h2
    md = _markdown(md_path, baselevel=2)
    article_content = md.convert(md_path.read_text())

    data = _article_data(md_path, md.Meta)

    # Paths

    build_dir = _BUILD_DIR / data["slug"]
    build_dir.mkdir(parents=True, exist_ok=True)

    article_content_path = build_dir / f"{md_path.stem}.html"
    article_data_path = build_dir / f"{md_path.stem}.json"

    subninja_path = build_dir / "build.ninja"

    dist_path = _DIST_DIR / pathlib.Path(data["fs_path"]).relative_to("/")
    distdir_path = dist_path.parent
    distdir_path.mkdir(parents=True, exist_ok=True)

    article_content_path.write_text(article_content)

    data["content_path"] = str(article_content_path)

    # TILs are also nested in the TIL page, under an h2 title: there their
    # headings start at h3
    if data["category"] == "til":
        nested_content = _markdown(md_path, baselevel=3).convert(md_path.read_text())
        nested_content_path = build_dir / f"{md_path.stem}.nested.html"
        nested_content_path.write_text(nested_content)
        data["nested_content_path"] = str(nested_content_path)

    # Write article data json

    print(f"Generating: {md_path} -> {build_dir}")

    with article_data_path.open("w") as fp:
        json.dump(data, fp, indent=2, sort_keys=True)

    # Writing article build ninja

    with _mkdir_open(subninja_path, "w") as fp:
        _render(
            fp,
            "article-build.ninja.j2",
            slug=data["slug"],
            dist_path=safe_ninja(dist_path),
            render_html_deps=_RENDER_HTML_DEPS,
            media_paths=[
                (
                    media_command,
                    safe_ninja(md_path.parent / media_src),
                    safe_ninja(distdir_path / media_dst),
                    vars,
                )
                for media_command, media_src, media_dst, vars in md.MediaProcessor.srcs
            ],
        )

    _add_article_data_path(article_data_path)
    _add_subninja(subninja_path)

# Main build.ninja

main_build_ninja = _BUILD_DIR / "build.ninja"
print(f"Generating {main_build_ninja}")

with main_build_ninja.open("w") as fp:
    _ENV.get_template("main-build.ninja.j2").stream(
        bin_path=_BIN_DIR,
        theme_dir=_THEME_DIR,
        global_data_path=safe_ninja(_GLOBAL_DATA_PATH),
        stylesheets_path=safe_ninja(_STYLESHEETS_PATH),
        # The directory too: its modification time changes when a stylesheet
        # is added, removed or renamed
        stylesheet_paths=[safe_ninja(path) for path in [_STYLESHEETS_DIR, *stylesheet_srcs]],
        subninja_paths=[safe_ninja(path) for path in _SUBNINJA_PATHS],
        article_data_paths=[safe_ninja(path) for path in _ARTICLES_DATA_PATHS],
        all_articles_data_path=safe_ninja(_BUILD_DIR / "all_articles_data.json"),
    ).dump(fp)
