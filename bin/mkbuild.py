import copy
import json
import pathlib
import re
from contextlib import contextmanager

import jinja2
import markdown
import yaml

_REPO_DIR = pathlib.Path(__file__).parent.parent.absolute()
_BIN_DIR = _REPO_DIR / "bin"
_BUILD_DIR = _REPO_DIR / "build"
_DIST_DIR = _BUILD_DIR / "dist"
_CONTENT_DIR = _REPO_DIR / "content/content"
_NINJA_TEMPLATES_DIR = _REPO_DIR / "templates/ninja"
_THEME_DIR = _REPO_DIR / "templates/theme"
_THEME_STATIC_DIR = _THEME_DIR / "static"
_GLOBAL_DATA_PATH = _REPO_DIR / "global.yml"

with _GLOBAL_DATA_PATH.open("r") as fp:
    _GLOBAL_DATA = yaml.safe_load(fp)

_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_NINJA_TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(),
)

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


# _BUILD_DIR.mkdir(exist_ok=True, parents=True)

# Copy static theme

static_paths = [
    (
        src,
        _DIST_DIR / src.relative_to(_THEME_STATIC_DIR),
    )
    for src in _THEME_STATIC_DIR.glob("**/*")
    if src.is_file()
]
static_build_path = _BUILD_DIR / "static.ninja"
with _mkdir_open(static_build_path, "w") as fp:
    _render(fp, "static-build.ninja.j2", static_paths=static_paths)
_add_subninja(static_build_path)

# Make articles build.ninja

for md_path in _CONTENT_DIR.glob("**/*.md"):
    # Extracting article data from path

    data_from_path = {}
    m = re.match(
        r".*?/(?P<category>\w+)/((?P<date>\d{4}-\d{2}-\d{2})-)?(?P<slug>[a-z0-9-]+)/(?P<lang>fr|en).md$",
        str(pathlib.PurePosixPath(md_path)),
    )
    if m is None:
        raise RuntimeError(f"Failed to parse {md_path}")
    data_from_path.update(m.groupdict())
    if data_from_path["date"] is None:
        data_from_path["date"] = ""

    if data_from_path["category"] == "page":
        data_from_path["path"] = f"/{data_from_path['slug']}.html"
    else:
        data_from_path["path"] = f"/{data_from_path['slug']}/index.html"

    build_dir = _BUILD_DIR / data_from_path["slug"]
    build_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating: {md_path} -> {build_dir}")

    article_content_path = build_dir / f"{md_path.stem}.html"
    article_data_path = build_dir / f"{md_path.stem}.json"

    md = markdown.Markdown(extensions=["meta"])
    article_content_path.write_text(md.convert(md_path.read_text()))

    data = copy.deepcopy(md.Meta)
    for key, value in data.items():
        if len(value) == 1:
            data[key] = value[0]
    data["content_path"] = str(article_content_path)

    # data_from_path_path = build_dir / "data_from_path.json"

    with article_content_path.open("w") as fp:
        json.dump(data, fp, indent=2, sort_keys=True)

    # Writing article build.ninja

    subninja_path = build_dir / "build.ninja"

    # step2_subninja_path = build_dir / "step2.ninja"
    # step2_subninja_path.parent.mkdir(parents=True, exist_ok=True)
    # step2_subninja_path.touch()

    dist_path = _DIST_DIR / pathlib.Path(data_from_path["path"]).relative_to("/")
    # article_data_path = subninja_path.parent / "data.json"
    # article_data_path.touch()

    with _mkdir_open(subninja_path, "w") as fp:
        _render(
            fp,
            "article-build.ninja.j2",
            build_dir=subninja_path.parent,
            # step2_subninja_path=step2_subninja_path,
            global_data_path=_GLOBAL_DATA_PATH,
            # data_from_path=data_from_path_path,
            article_data_path=article_data_path,
            md_path=md_path,
            dist_path=dist_path,
            dist_dir=dist_path.parent,
        )

    _add_article_data_path(article_data_path)
    _add_subninja(subninja_path)

# Main build.ninja

main_build_ninja = _BUILD_DIR / "build.ninja"
print(f"Generating {main_build_ninja}")

main_step2_subninja_path = _BUILD_DIR / "step2.ninja"
main_step2_subninja_path.touch()

with main_build_ninja.open("w") as fp:
    _ENV.get_template("main-build.ninja.j2").stream(
        bin_path=_BIN_DIR,
        theme_dir=_THEME_DIR,
        default_template=_GLOBAL_DATA["default_template"],
        subninja_paths=_SUBNINJA_PATHS,
        article_data_paths=_ARTICLES_DATA_PATHS,
        all_articles_data_path=_BUILD_DIR / "all_articles_data.json",
        main_step2_subninja_path=main_step2_subninja_path,
    ).dump(fp)
