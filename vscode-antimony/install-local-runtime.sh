#!/usr/bin/env bash
#
# Install a locally built runtime into VS Code's globalStorage, the same place
# the extension would install a downloaded one.
#
# Writes the .installed marker LAST, and only after the interpreter has been
# verified. A partial or interrupted extraction therefore leaves no marker, so
# the extension treats it as "not installed" and re-installs rather than
# starting a language server against a half-unpacked stdlib.
#
# Usage, from vscode-antimony/:
#     bash install-local-runtime.sh

set -euo pipefail

ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
  PLATFORM="darwin-arm64"
else
  PLATFORM="darwin-x64"
fi

TARBALL="runtime-dist/antimony-runtime-1-${PLATFORM}.tar.gz"
DEST="$HOME/Library/Application Support/Code/User/globalStorage/stevem.vscode-antimony/runtime/1"

if [ ! -f "$TARBALL" ]; then
  echo "error: $TARBALL not found. Run:"
  echo "    python3 scripts/build_runtime.py --platform $PLATFORM"
  exit 1
fi

echo "==> removing any previous install"
rm -rf "$DEST"
mkdir -p "$DEST"

echo "==> extracting $TARBALL"
tar xzf "$TARBALL" -C "$DEST"

PY="$DEST/python/bin/python3"

echo "==> verifying interpreter"
if [ ! -x "$PY" ]; then
  echo "error: no interpreter at $PY -- extraction failed"
  rm -rf "$DEST"
  exit 1
fi

# Orphaned .pth from an older build_runtime.py that pruned _distutils_hack
# while keeping setuptools. Harmless to remove if absent.
rm -f "$DEST/python/lib/python3.10/site-packages/distutils-precedence.pth"

echo "==> verifying the imports the language server needs"
"$PY" - <<'PYCHECK'
import antimony, libsbml, pygls, orjson
from bioservices import ChEBI
# The path that failed at runtime: pygls builds this lazily on the first
# workspace/executeCommand, so imports alone do not cover it.
from multiprocessing.pool import ThreadPool
ThreadPool(2).close()
print("    imports OK, ThreadPool OK")
PYCHECK

echo "==> writing marker"
printf '1\nlocal\n' > "$DEST/.installed"

echo
echo "installed and verified:"
echo "  $PY"
echo
echo "Press F5. Expect: [antimony] runtime root: ... (marker: true, interpreter: true)"