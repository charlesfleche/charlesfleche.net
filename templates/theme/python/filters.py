from pathlib import Path


def read_text(path):
    return Path(path).read_text()
