#!/usr/bin/env bash
# Fetches the wheel of a version as an index gives it, the index being slow to
# list what was just published, and prints its path. A wheel of the same name
# in dist/, the build a release workflow tested, must be the same file.
#
#   fetch_wheel.sh PACKAGE VERSION DEST
#
# INDEX is the index, TestPyPI by default; PYTHON runs pip, which refuses a
# wheel its interpreter does not support; ATTEMPTS, ten seconds apart.
set -eu -o pipefail

package=$1
version=$2
dest=$3
index=${INDEX:-https://test.pypi.org/simple/}
python=${PYTHON:-3.14}
attempts=${ATTEMPTS:-50}

mkdir -p "$dest"
for attempt in $(seq "$attempts"); do
    uvx --quiet --python "$python" pip download --quiet --no-deps --only-binary :all: \
        --index-url "$index" --dest "$dest" "$package==$version" >&2 && break
    [ "$attempt" -lt "$attempts" ] || exit 1
    echo "== waiting for $package $version on $index" >&2
    sleep 10
done

wheel=$(echo "$dest"/*.whl)
if [ -f "dist/${wheel##*/}" ]; then
    cmp "$wheel" "dist/${wheel##*/}" >&2
    echo "== ${wheel##*/} is the build of dist/" >&2
fi
echo "$wheel"
