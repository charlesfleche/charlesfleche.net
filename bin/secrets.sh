#!/bin/bash
# The secrets of the scripts of charlesfleche.net (Mastodon, Instagram, TMDB),
# encrypted with age to the ssh keys of secrets.recipients, in secrets.env.age.
#
#   bin/secrets.sh edit             decrypts them in the editor of git, then
#                                   encrypts them again if they changed
#   bin/secrets.sh rekey            encrypts them again to secrets.recipients:
#                                   after a key is added or removed. A removed
#                                   key could still decrypt the old versions
#                                   in git: change the secrets themselves too
#   bin/secrets.sh run COMMAND...   runs COMMAND with the secrets in its
#                                   environment, and nowhere else.
#                                   CHARLESFLECHE_SECRETS lists their names
#
# The plain text is one KEY=value per line, the value verbatim to the end of
# the line, without quotes. Empty lines and lines starting with # are ignored.
# The private key is ~/.ssh/id_ed25519, or CHARLESFLECHE_SECRETS_IDENTITY.

set -euo pipefail

root="$(dirname "$(dirname "$(readlink -f "$0")")")"
secrets="$root/secrets.env.age"
recipients="$root/secrets.recipients"
identity="${CHARLESFLECHE_SECRETS_IDENTITY:-$HOME/.ssh/id_ed25519}"

die() {
    echo "secrets.sh: $*" >&2
    exit 1
}

decrypt() {
    age --decrypt --identity "$identity" "$secrets"
}

# Writes stdin, the plain text, to secrets.env.age, encrypted to every key of
# secrets.recipients
encrypt() {
    age --encrypt --recipients-file "$recipients" --output "$secrets.tmp"
    mv "$secrets.tmp" "$secrets"
}

# Fails on the first line of the plain text $1 that is not KEY=value
check() {
    local line number=0
    while IFS= read -r line; do
        number=$((number + 1))
        [[ -z "$line" || "$line" == \#* ]] && continue
        [[ "$line" =~ ^[A-Z][A-Z0-9_]*= ]] || die "line $number is not KEY=value"
    done <<<"$1"
}

[[ $# -ge 1 ]] || die "usage: secrets.sh edit | rekey | run COMMAND..."
command="$1"
shift

case "$command" in
edit)
    [[ $# -eq 0 ]] || die "edit takes no argument"
    # In memory, readable by the user only, removed on exit
    umask 077
    tmp="$(mktemp -d /dev/shm/charlesfleche-secrets.XXXXXX)"
    trap 'rm -rf "$tmp"' EXIT
    if [[ -e "$secrets" ]]; then
        decrypt >"$tmp/secrets.env"
    else
        : >"$tmp/secrets.env"
    fi
    cp "$tmp/secrets.env" "$tmp/before"
    # As git runs it: the editor may hold arguments
    sh -c "$(git -C "$root" var GIT_EDITOR)"' "$@"' editor "$tmp/secrets.env"
    if cmp -s "$tmp/before" "$tmp/secrets.env"; then
        echo "secrets.sh: no change"
        exit 0
    fi
    check "$(cat "$tmp/secrets.env")"
    encrypt <"$tmp/secrets.env"
    echo "secrets.sh: $secrets changed: commit and push it"
    ;;
rekey)
    [[ $# -eq 0 ]] || die "rekey takes no argument"
    plain="$(decrypt)"
    check "$plain"
    encrypt <<<"$plain"
    echo "secrets.sh: $secrets encrypted to $recipients: commit and push it"
    ;;
run)
    [[ $# -ge 1 ]] || die "run needs a command"
    plain="$(decrypt)"
    check "$plain"
    names=()
    while IFS= read -r line; do
        [[ -z "$line" || "$line" == \#* ]] && continue
        export "${line%%=*}=${line#*=}"
        names+=("${line%%=*}")
    done <<<"$plain"
    # Their names, for COMMAND to keep them out of its own child processes
    export CHARLESFLECHE_SECRETS="${names[*]}"
    unset plain line names
    exec "$@"
    ;;
*)
    die "unknown command $command: edit, rekey or run"
    ;;
esac
