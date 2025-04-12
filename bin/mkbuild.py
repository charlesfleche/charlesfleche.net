import pathlib

import jinja2

_REPO_DIR = pathlib.Path(__file__).parent.parent.absolute()
_BIN_DIR = _REPO_DIR / "bin"
_BUILD_DIR = _REPO_DIR / "build"
_DIST_DIR = _BUILD_DIR / "dist"
_CONTENT_DIR = _REPO_DIR / "content/content"
_NINJA_TEMPLATES_DIR = _REPO_DIR / "templates/ninja"
_STATIC_DIR = _REPO_DIR / "templates/theme/static"
_THEME_TEMPLATES_DIR = _REPO_DIR / "templates/theme/templates"

_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_NINJA_TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(),
)

_SUBNINJA_PATHS = []

_BUILD_DIR.mkdir(exist_ok=True, parents=True)

# Copy static theme

static_paths = [
    (
        src,
        _DIST_DIR / src.relative_to(_STATIC_DIR),
    )
    for src in _STATIC_DIR.glob("**/*")
    if src.is_file()
]
static_build_path = _BUILD_DIR / "static.ninja"
with static_build_path.open("w") as fp:
    _ENV.get_template("static-build.ninja.j2").stream(
        static_paths=static_paths,
    ).dump(fp)
_SUBNINJA_PATHS.append(static_build_path)

# Make articles build.ninja

for md_path in _CONTENT_DIR.glob("*/**/*.md"):
    rel_dst_dir = md_path.parent.relative_to(_CONTENT_DIR)
    abs_dst_dir = _BUILD_DIR / rel_dst_dir

    abs_dst_dir.mkdir(exist_ok=True, parents=True)

    subninja_path = abs_dst_dir / "build.ninja"

    with subninja_path.open("w") as fp:
        _ENV.get_template("article-build.ninja.j2").stream(
            data_path=abs_dst_dir / f"{md_path.stem}.json",
            md_path=md_path,
            html_path=_DIST_DIR / rel_dst_dir / "index.html",
            template_path=_THEME_TEMPLATES_DIR / "article.html.j2",
        ).dump(fp)

    _SUBNINJA_PATHS.append(subninja_path)

# Main build.ninja

with (_BUILD_DIR / "build.ninja").open("w") as fp:
    _ENV.get_template("main-build.ninja.j2").stream(
        bin_path=_BIN_DIR,
        subninja_paths=_SUBNINJA_PATHS,
    ).dump(fp)
