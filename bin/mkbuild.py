import json
import pathlib
import re

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

for md_path in _CONTENT_DIR.glob("**/*.md"):
    # Extracting article local data from path

    local_data = {}
    local_data_path = None
    html_path = (_DIST_DIR / md_path.stem).with_suffix(".html")
    if m := re.match(
        r".*?/(?P<group>\w+)/(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9-]+)/(?P<lang>fr|en).md$",
        str(md_path),
    ):
        local_data = m.groupdict()
        html_path = _DIST_DIR / local_data["slug"] / "index.html"
    else:
        local_data["slug"] = md_path.with_suffix(".html").name

    # Paths

    if md_path.parent == _CONTENT_DIR:
        rel_dst_dir = md_path.stem
    else:
        rel_dst_dir = md_path.parent.relative_to(_CONTENT_DIR)
    abs_dst_dir = _BUILD_DIR / rel_dst_dir
    local_data_path = abs_dst_dir / "local.json"
    subninja_path = abs_dst_dir / "build.ninja"

    # Ensure the build folder is ready

    print(f"Generating: {md_path} -> {abs_dst_dir}")

    abs_dst_dir.mkdir(exist_ok=True, parents=True)

    with local_data_path.open("w") as fp:
        json.dump(local_data, fp)

    # Writing article build.ninja

    with subninja_path.open("w") as fp:
        _ENV.get_template("article-build.ninja.j2").stream(
            global_data_path=_REPO_DIR / "global.yml",
            local_data_path=local_data_path,
            data_path=abs_dst_dir / f"{md_path.stem}.json",
            md_path=md_path,
            html_path=html_path,
            template_path=_THEME_TEMPLATES_DIR / "article.html.j2",
        ).dump(fp)

    _SUBNINJA_PATHS.append(subninja_path)

# Main build.ninja

main_build_ninja = _BUILD_DIR / "build.ninja"
print(f"Generating {main_build_ninja}")

with main_build_ninja.open("w") as fp:
    _ENV.get_template("main-build.ninja.j2").stream(
        bin_path=_BIN_DIR,
        subninja_paths=_SUBNINJA_PATHS,
    ).dump(fp)
