Title: Making git blame skip reformatting commits
Description: .git-blame-ignore-revs, to reformat a whole codebase without losing its history
Tags: [git, github, clang-format, claude]

While modernizing [lpd8editor](https://github.com/charlesfleche/lpd8editor), I asked Claude to reformat the whole tree with clang-format. I was worried about losing `git blame`: every line touched by the reformat would point to that one mechanical commit, not to the change that actually wrote the code. Claude followed the reformat with [a second commit](https://github.com/charlesfleche/lpd8editor/commit/04af0e556a7eddc4a498d3bf2d409006fbf42727) that adds a `.git-blame-ignore-revs` file at the root of the repository:

```bash
# Commits that 'git blame' should skip: mechanical changes such as
# reformatting, so blame shows who last changed the code itself.
#
# GitHub reads this file automatically. For local git, run once:
#   git config blame.ignoreRevsFile .git-blame-ignore-revs

# Reformat the sources with clang-format
f458c1178b423a46cc8e07bfe41a62dd75efd9f0
```

It lists one full commit hash per line, comments allowed. `git blame` skips those commits and blames each line on the commit that changed it before.

GitHub's blame view reads the file automatically. git itself doesn't, so each clone needs this setting once:

```bash
$ git config blame.ignoreRevsFile .git-blame-ignore-revs
```

The same can be done for a single run with `git blame --ignore-revs-file .git-blame-ignore-revs`, or `--ignore-rev <commit>` for a single commit.

The reformat and the file have to be two commits: a commit can't contain its own hash. Also, the reformat should change nothing but the formatting, or the real changes hidden in it would be skipped as well.
