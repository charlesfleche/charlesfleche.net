Title: Replacing griffo with latest-debs
Description: Up to date developer tools on Debian, still free
Tags: [linux, debian, apt, extrepo]

I've been using [griffo](https://debian.griffo.io/) to get recent versions of `neovim`, `lazygit`, `fzf`, `ripgrep`, `uv` and friends on Debian stable. Starting October 1st 2026, downloading packages from griffo requires a subscription. A free `griffo-free` repository remains, but it lags at least two months behind upstream releases.

[latest-debs](https://latest-debs.ranjithraj.workers.dev/) is a free alternative: it tracks the latest stable releases of developer tools (`uv`, `eza`, `lazygit`, `neovim`…) and packages them for Debian. It covered everything I was getting from griffo.

Both repositories are available through [extrepo](https://salsa.debian.org/extrepo-team/extrepo), so switching is a matter of disabling one and enabling the other:

```bash
# Remove griffo
sudo extrepo disable griffo
sudo rm /etc/apt/sources.list.d/extrepo_griffo.sources

# Add latest-debs
sudo extrepo enable latest-debs
sudo apt update
sudo apt full-upgrade
```

`extrepo disable` only marks the source as disabled, hence the `rm` to get rid of it entirely.

Before switching, this lists the installed packages whose candidate version comes from griffo, to check what needs to come from the new repository:

```bash
dpkg-query -W -f='${Package}\n' | xargs apt-cache policy | awk '
/^[^ ]/ { pkg = $1 }
/\*\*\*/ {
    getline
    if ($0 ~ /griffo/) {
        print pkg
    }
}'
```

The extrepo setup worked just fine: `apt full-upgrade` picked up the latest-debs versions, and checking the origin afterwards confirms where they come from:

```bash
$ aptitude search '?installed?origin(latest-debs)'
i  fzf - A command-line fuzzy finder
i  git-delta - A syntax-highlighting pager…
i  lazygit - simple terminal UI for git…
i  neovim - A heavily refactored vim fork…
i  ripgrep - ripgrep recursively searches…
i  uv - An extremely fast Python package…
```
