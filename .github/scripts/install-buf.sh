#!/usr/bin/env bash
# Installs the Buf CLI of the version the ecosystem pins,
# .github/actions/setup-buf/version, as <dir>/buf: the binary of the platform
# from the releases of Buf, checked by the checksums the release publishes.
# Does nothing if <dir>/buf is there already: the directory names the version.
set -euo pipefail

dir=${1:?usage: install-buf.sh <dir>}
[ -x "$dir/buf" ] && exit 0
version=$(cat "$(dirname "$0")/../actions/setup-buf/version")

case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) asset=buf-Linux-x86_64 ;;
    Linux-aarch64 | Linux-arm64) asset=buf-Linux-aarch64 ;;
    Darwin-arm64) asset=buf-Darwin-arm64 ;;
    Darwin-x86_64) asset=buf-Darwin-x86_64 ;;
    *) echo "no Buf for $(uname -s) $(uname -m)" >&2; exit 1 ;;
esac

url=https://github.com/bufbuild/buf/releases/download/v$version
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -o "$tmp/$asset" "$url/$asset"
curl -fsSL -o "$tmp/sha256.txt" "$url/sha256.txt"
if command -v sha256sum >/dev/null; then
    sum=(sha256sum)
else
    sum=(shasum -a 256)  # macOS
fi
(cd "$tmp" && grep " $asset\$" sha256.txt | "${sum[@]}" -c --quiet -)
mkdir -p "$dir"
install -m 755 "$tmp/$asset" "$dir/buf"
