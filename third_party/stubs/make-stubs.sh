#!/bin/sh
# Create link-time symlinks for libraries that some distros only ship as
# runtime `.so.0` files (no -dev package installed).
#
# gpui links against `libxkbcommon` and `libxkbcommon-x11` by their unversioned
# names, which the linker resolves through `lib<x>.so`. Debian's runtime package
# ships only `libxkbcommon.so.0`, so linking fails with
# "unable to find library -lxkbcommon" even though the library is installed.
#
# This script creates `lib<x>.so -> lib<x>.so.N` inside this directory, and
# `.cargo/config.toml` adds it to the linker search path. Nothing is copied or
# vendored; the links point at your system libraries.
#
# You do not need this if you have libxkbcommon-dev and libxkbcommon-x11-dev
# installed - in that case delete `.cargo/config.toml`'s rustflags entry and this
# directory.
#
#     sh third_party/stubs/make-stubs.sh
set -e

here=$(cd "$(dirname "$0")" && pwd)
found=0

for lib in xkbcommon xkbcommon-x11; do
    real=$(ls /usr/lib/*/lib"$lib".so.* 2>/dev/null | head -1)
    if [ -z "$real" ]; then
        real=$(ls /usr/lib/lib"$lib".so.* 2>/dev/null | head -1)
    fi
    if [ -n "$real" ]; then
        ln -sf "$real" "$here/lib$lib.so"
        echo "lib$lib.so -> $real"
        found=$((found + 1))
    else
        echo "warning: lib$lib.so.* not found - install lib$lib (or its -dev package)" >&2
    fi
done

if [ "$found" -eq 0 ]; then
    echo "nothing linked; if you have the -dev packages, drop the rustflags in .cargo/config.toml" >&2
    exit 1
fi
