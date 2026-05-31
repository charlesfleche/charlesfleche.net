#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2"]
# ///
"""
newcontent.py — Initialize a markdown file for a static blog generator.

Usage:
    uvx bin/newcontent.py "The title of my new content"
    uvx bin/newcontent.py "My Post" --category tutorial --lang fr
    uvx bin/newcontent.py "My Post" --date 2026-06-15

Output path:
    content/[category]/[year-month-day]-[slug]/[lang].md

Template lookup order (first match wins):
    templates/content/[category].[lang].md.j2
    templates/content/[category].md.j2
    templates/content/default.[lang].md.j2
    templates/content/default.md.j2
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_ROOT_DIR = Path(__file__).parent.parent
_TEMPLATES_DIR = _ROOT_DIR / "templates" / "content"
_DRAFT_DIR = _ROOT_DIR / "content" / "draft"

_ENV = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


def slugify(text: str) -> str:
    """Convert a title to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def render_content(**context) -> str:
    return _ENV.get_template("content.md.j2").render(**context)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize a markdown file for a static blog post.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example:\n  uvx bin/newcontent.py "My Post" --category tutorial --lang fr',
    )
    parser.add_argument("title", nargs="+", help="Title of the new content")
    parser.add_argument(
        "--category",
        "-c",
        default="article",
        help="Content category (default: article)",
    )
    parser.add_argument(
        "--lang", "-l", default="en", help="Language code (default: en)"
    )
    parser.add_argument(
        "--date",
        "-d",
        type=date.fromisoformat,
        default=date.today(),
        help="Publication date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print the output path and rendered content without creating any files",
    )

    args = parser.parse_args()

    title = " ".join(args.title)
    slug = slugify(title)
    folder_name = f"{args.date.strftime('%Y-%m-%d')}-{slug}"
    output_path = _DRAFT_DIR / args.category / folder_name / f"{args.lang}.md"

    content = render_content(title=title)

    if args.dry_run:
        print(f"[dry-run] Would create: {output_path}")
        print("-" * 40)
        print(content)
        return

    if output_path.exists():
        print(f"Error: file already exists: {output_path}", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
