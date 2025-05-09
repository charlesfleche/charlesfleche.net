import itertools
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

_REPO_DIR = pathlib.Path(__file__).parent.parent.absolute()
_BIN_DIR = _REPO_DIR / "bin"
_BUILD_DIR = _REPO_DIR / "build"
_DIST_DIR = _BUILD_DIR / "dist"
_CONTENT_DIR = _REPO_DIR / "content/content"
_NINJA_TEMPLATES_DIR = _REPO_DIR / "templates/ninja"
_THEME_DIR = _REPO_DIR / "templates/theme"
_THEME_STATIC_DIR = _THEME_DIR / "static"
_GLOBAL_DATA_PATH = _REPO_DIR / "global.yml"

_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_NINJA_TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(),
)


def safe_ninja(path):
    path = pathlib.PurePosixPath(path)
    return re.sub(r"[:$]", r"$\g<0>", str(path))


_ENV.filters["safe_ninja"] = safe_ninja


_SUBNINJA_PATHS = []
_ARTICLES_DATA_PATHS = []


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
    _TAGS = {
        "image": "picture",
    }
    _ATTRS = {
        "video": [
            ("controls", "controls"),
        ]
    }
    _SRC_ATTRS = {
        "picture": {"src": "srcset"},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.srcs = []

    def run(self, root):
        for element in root.iter("img"):
            attrib = element.attrib

            if data := self._src(attrib.get("src", "")):
                tag, attrs, src_attrs = data
                tail = element.tail
                element.clear()
                element.tag = tag
                element.tail = tail

                del attrib["src"]

                for src_attrs in src_attrs:
                    source = ET.SubElement(element, "source")
                    for k, v in src_attrs.items():
                        source.set(k, v)

                for k, v in itertools.chain(attrs, attrib.items()):
                    element.set(k, v)

    def _src(self, src):
        typ, _ = mimetypes.guess_type(src)
        if m := re.match(r"^(image|video)/.*$", typ):
            tag = m.groups()[0]
            tag = self._TAGS.get(tag, tag)

            attrs = self._ATTRS.get(tag, [])

            srcs_attrs = [
                {
                    self._SRC_ATTRS.get(tag, {}).get("src", "src"): src,
                    self._SRC_ATTRS.get(tag, {}).get("type", "type"): typ,
                }
            ]

            self.srcs.append(pathlib.Path(src))

            return tag, attrs, srcs_attrs


class MdExtension(Extension):
    def extendMarkdown(self, md):
        md.MediaProcessor = MediaProcessor(md)
        md.treeprocessors.register(
            md.MediaProcessor,
            "mediaprocessor",
            20,  # <= 20 to run after img processor
        )


# Copy static theme

static_paths = [
    (
        safe_ninja(src),
        safe_ninja(_DIST_DIR / src.relative_to(_THEME_STATIC_DIR)),
    )
    for src in _THEME_STATIC_DIR.glob("**/*")
    if src.is_file()
]
static_build_path = _BUILD_DIR / "static.ninja"
with _mkdir_open(static_build_path, "w") as fp:
    _render(fp, "static-build.ninja.j2", static_paths=static_paths)
_add_subninja(static_build_path)

# Make articles build.ninja

for md_path in _CONTENT_DIR.glob("*/*/*.md"):
    # Parsing article's markdown

    md = markdown.Markdown(
        extensions=[
            "codehilite",
            "meta",
            "fenced_code",
            MdExtension(),
        ]
    )

    article_content = md.convert(md_path.read_text())

    data = {}
    for key, value in md.Meta.items():
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
        data["path"] = data.get("path", f"/{data['slug']}.html")
        data["fs_path"] = data["path"]
    else:
        data["path"] = data.get("path", f"/{data['slug']}")
        data["fs_path"] = f"{data['path']}/index.html"

    # Paths

    build_dir = _BUILD_DIR / data["slug"]
    build_dir.mkdir(parents=True, exist_ok=True)

    article_content_path = build_dir / f"{md_path.stem}.html"
    article_data_path = build_dir / f"{md_path.stem}.json"

    subninja_path = build_dir / "build.ninja"

    dist_path = _DIST_DIR / pathlib.Path(data["fs_path"]).relative_to("/")
    distdir_path = dist_path.parent

    article_content_path.write_text(article_content)

    data["content_path"] = str(article_content_path)

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
            media_paths=[
                (
                    safe_ninja(md_path.parent / path.name),
                    safe_ninja(distdir_path / path.name),
                )
                for path in md.MediaProcessor.srcs
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
        subninja_paths=[safe_ninja(path) for path in _SUBNINJA_PATHS],
        article_data_paths=[safe_ninja(path) for path in _ARTICLES_DATA_PATHS],
        all_articles_data_path=safe_ninja(_BUILD_DIR / "all_articles_data.json"),
    ).dump(fp)
