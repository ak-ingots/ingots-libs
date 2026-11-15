# Sourced by the scripts: the meta checkout, its repositories, the network
# commands under the token of its .envrc.
set -euo pipefail
meta=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

die() { echo "$*" >&2; exit 1; }

# gh and network git with the token; direnv's own log dropped
net() { direnv exec "$meta" "$@" 2> >(grep -v 'direnv: ' >&2); }

# cd into a repository by its name, "." for the meta itself
enter() {
    if [ "$1" = . ]; then cd "$meta"; else cd "$meta/$1"; fi
    name=$(basename "$PWD")
}

# once the pull request of the current branch is merged: main pulled, the
# branch deleted; prints the merge commit, fails while it is open. The
# steps check themselves, as a caller testing it turns errexit off.
finish_branch() {
    local branch info pr state head merge
    branch=$(git branch --show-current)
    [ "$branch" != main ] || die "$name: on main"
    info=$(net gh pr view "$branch" --json number,state,headRefOid,mergeCommit \
        --jq '"\(.number) \(.state) \(.headRefOid) \(.mergeCommit.oid // "-")"' \
        2> /dev/null) || die "$name: $branch has no pull request"
    read -r pr state head merge <<< "$info"
    [ "$state" = MERGED ] || die "$name: $branch, #$pr $state"
    [ "$(git rev-parse HEAD)" = "$head" ] || die "$name: $branch beyond #$pr"
    git switch -q main || die "$name: cannot switch to main"
    net git pull -q --ff-only || die "$name: cannot pull main"
    git branch -q -D "$branch" || die "$name: cannot delete $branch"
    echo "$merge"
}
