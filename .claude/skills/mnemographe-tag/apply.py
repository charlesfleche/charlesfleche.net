#!/usr/bin/env python3
"""The editor of mnemographe-tag for the mnemographe-tag skill: apply.py TAGS ALTS FILE.

TAGS has one line per photo, "<stem> <tag> <tag> ...". ALTS has one line per
photo, "<file name>|<alt text>". Either file may be "-" for none. In FILE, the
file that mnemographe-tag opens, it fills the empty tags and the empty alt text
of these photos. It stops, writing nothing, if one of them already has tags or
an alt text that it would replace, or is not in FILE.
"""

import sys


def read(path: str, separator: str) -> dict[str, str]:
    if path == "-":
        return {}
    with open(path, encoding="utf-8") as lines:
        return dict(line.rstrip("\n").split(separator, 1) for line in lines if line.strip())


def main() -> None:
    tags_path, alts_path, path = sys.argv[1:]
    tags = read(tags_path, " ")
    alts = read(alts_path, "|")
    out, done = [], set()
    with open(path, encoding="utf-8") as lines:
        for line in lines:
            if line.startswith("#") or not line.strip():
                out.append(line)
                continue
            head, _, alt = line.rstrip("\n").partition("|")
            words = head.split()
            name = words[1]
            stem = name.rsplit(".", 1)[0]
            line_tags, alt = words[2:], alt.strip()
            if stem in tags:
                if line_tags:
                    sys.exit(f"{name} already has tags: {' '.join(line_tags)}")
                line_tags = tags[stem].split()
                done.add(stem)
            if name in alts:
                if alt:
                    sys.exit(f"{name} already has an alt text: {alt}")
                alt = alts[name]
                done.add(name)
            line = f"{words[0]} {name} {' '.join(line_tags)}".rstrip()
            out.append(f"{line} | {alt}\n" if alt else f"{line}\n")
    missing = (set(tags) | set(alts)) - done
    if missing:
        sys.exit(f"not in the editor file: {', '.join(sorted(missing))}")
    with open(path, "w", encoding="utf-8") as file:
        file.writelines(out)


if __name__ == "__main__":
    main()
