#!/usr/bin/env python3
"""
Build a self-contained, relocatable Python runtime for vscode-antimony.

Run once per platform on a matching CI runner. Produces:

    dist/antimony-runtime-<RUNTIME_VERSION>-<platform>.tar.gz
    dist/antimony-runtime-<RUNTIME_VERSION>-<platform>.tar.gz.sha256

The resulting tarball contains a `python/` directory that runs anywhere, with
every dependency already installed. The end user's machine needs no Python,
no pip, no venv, no git, and no admin rights.

Usage (from the repo root):
    python scripts/build_runtime.py --platform darwin-arm64

Platforms: win32-x64, darwin-x64, darwin-arm64, linux-x64
"""

import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

# Bump this whenever the runtime contents change. The extension compares it
# against what it has on disk and reinstalls on mismatch, so this is the one
# knob that controls user-visible re-downloads.
RUNTIME_VERSION = "1"

# python-build-standalone release. These are the relocatable CPython builds
# that uv uses. Pinned so builds are reproducible.
PBS_RELEASE = "20260814"
PYTHON_VERSION = "3.10.21"

# Python 3.10 rather than something newer: pygls 0.9.1 and pre-1.0 lark are
# both required by the server code and neither is maintained. 3.10 is the
# newest interpreter the pinned stack was verified against.

PBS_TRIPLES = {
    "win32-x64": "x86_64-pc-windows-msvc",
    "darwin-x64": "x86_64-apple-darwin",
    "darwin-arm64": "aarch64-apple-darwin",
    "linux-x64": "x86_64-unknown-linux-gnu",
}

# See the platform-floor note in requirements-runtime.txt.
ANTIMONY_OVERRIDE = {
    "darwin-x64": "antimony==3.1.0",
}

# Stdlib pieces the language server never touches. Dropping these saves a
# meaningful chunk of the download.
PRUNE_STDLIB = ["test", "idlelib", "tkinter", "lib2to3", "ensurepip", "turtledemo"]

# ROOT is the extension directory (vscode-antimony/), i.e. the parent of
# scripts/. requirements-runtime.txt and src/server/ are resolved relative to it.
ROOT = Path(__file__).resolve().parent.parent

# Deliberately NOT "dist": webpack already writes the bundled extension to
# vscode-antimony/dist, and that path is gitignored. Sharing it would mean the
# runtime build clobbers extension.js.
DIST = ROOT / "runtime-dist"
BUILD = ROOT / "runtime-build"
CACHE = ROOT / "runtime-cache"


def log(msg):
    print(f"[build_runtime] {msg}", flush=True)


def preflight():
    """Check every input the build needs before doing anything expensive.

    Downloading and unpacking a 42 MB interpreter only to discover a missing
    file is a waste of the user's time, so validate first and fail with a
    message that says exactly what to do.
    """
    problems = []

    reqs = ROOT / "requirements-runtime.txt"
    if not reqs.is_file():
        problems.append(
            f"Missing: {reqs}\n"
            f"    requirements-runtime.txt belongs next to package.json, in the\n"
            f"    extension directory ({ROOT}).\n"
            f"    If you downloaded it elsewhere:  mv <path>/requirements-runtime.txt {reqs}"
        )

    server = ROOT / "src" / "server" / "main.py"
    if not server.is_file():
        problems.append(
            f"Missing: {server}\n"
            f"    build_runtime.py expects to sit in <extension>/scripts/, so that\n"
            f"    ROOT is the extension directory. ROOT currently resolves to {ROOT}."
        )

    stibium = ROOT / "src" / "server" / "stibium" / "stibium"
    if not stibium.is_dir():
        problems.append(
            f"Missing: {stibium}\n"
            f"    The smoke test imports stibium. Pass --skip-smoke-test to build anyway."
        )

    # RUNTIME_VERSION is duplicated in runtime.ts (the extension has no way to
    # read this file). If they drift, the extension downloads a URL that does
    # not exist, or installs into a directory it will never look in again.
    runtime_ts = ROOT / "src" / "runtime.ts"
    if runtime_ts.is_file():
        import re
        match = re.search(r"RUNTIME_VERSION\s*=\s*['\"]([^'\"]+)['\"]", runtime_ts.read_text())
        if match and match.group(1) != RUNTIME_VERSION:
            problems.append(
                f"RUNTIME_VERSION mismatch: this script says {RUNTIME_VERSION!r}, "
                f"src/runtime.ts says {match.group(1)!r}.\n"
                f"    They must match, or the extension will request a bundle that was never built."
            )

    if problems:
        log("cannot start, nothing was downloaded:")
        for problem in problems:
            print(f"\n  - {problem}", flush=True)
        print(flush=True)
        raise SystemExit(1)


def download(url, dest):
    log(f"downloading {url}")
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as fh:
        shutil.copyfileobj(resp, fh)


def fetch_python(platform, workdir):
    triple = PBS_TRIPLES[platform]
    name = f"cpython-{PYTHON_VERSION}+{PBS_RELEASE}-{triple}-install_only.tar.gz"
    url = (
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        f"{PBS_RELEASE}/{name}"
    )

    # Cached outside the build dir, which gets wiped on every run. The version
    # and release are both pinned, so a cache hit is always the right bytes and
    # a retry after a failed dependency install costs nothing.
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / name

    if archive.is_file():
        log(f"using cached interpreter ({archive.stat().st_size / 1_048_576:.0f} MiB)")
    else:
        download(url, archive)

    log("extracting interpreter")
    try:
        with tarfile.open(archive) as tf:
            tf.extractall(workdir)
    except tarfile.ReadError:
        # A truncated download would otherwise poison every later run.
        log("cached archive is corrupt, removing it -- run again")
        archive.unlink(missing_ok=True)
        raise

    return workdir / "python"


def interpreter_path(python_root, platform):
    if platform.startswith("win32"):
        return python_root / "python.exe"
    return python_root / "bin" / "python3"


def install_deps(py, platform):
    reqs = ROOT / "requirements-runtime.txt"
    log("installing dependencies")
    subprocess.run(
        [str(py), "-m", "pip", "install", "--disable-pip-version-check",
         "--no-cache-dir", "-r", str(reqs)],
        check=True,
    )
    override = ANTIMONY_OVERRIDE.get(platform)
    if override:
        log(f"applying platform override: {override}")
        subprocess.run(
            [str(py), "-m", "pip", "install", "--disable-pip-version-check",
             "--no-cache-dir", "--force-reinstall", "--no-deps", override],
            check=True,
        )


def smoke_test(py):
    """Import the server's real dependency graph. A bundle that cannot import
    is worse than no bundle -- it fails silently at LSP startup."""
    log("running smoke test")
    script = (
        "import sys, os\n"
        "sys.path.insert(0, os.path.join(%r, 'src', 'server', 'stibium'))\n"
        "import antimony, libsbml\n"
        "from stibium.parse import AntimonyParser\n"
        "from pygls.features import COMPLETION\n"
        "from pygls.server import LanguageServer\n"
        "from bioservices import ChEBI\n"
        "import orjson\n"
        # pygls.server.thread_pool builds a multiprocessing ThreadPool lazily,
        # on the first workspace/executeCommand. Startup and imports both
        # succeed without it, so only exercising imports lets an over-pruned
        # stdlib ship and fail later at the first user command.
        "from multiprocessing.pool import ThreadPool\n"
        "ThreadPool(2).close()\n"
        "p = AntimonyParser()\n"
        "p.parse('J0: A -> B; k1*A;\\nA = 10; k1 = 0.1;')\n"
        "print('smoke test OK')\n" % str(ROOT)
    )
    subprocess.run([str(py), "-c", script], check=True)


def prune(python_root, platform):
    log("pruning")
    if platform.startswith("win32"):
        libdir = python_root / "Lib"
    else:
        libdir = python_root / "lib" / f"python{PYTHON_VERSION.rsplit('.', 1)[0]}"

    for name in PRUNE_STDLIB:
        shutil.rmtree(libdir / name, ignore_errors=True)

    # pip is only needed at build time.
    #
    # Do NOT prune _distutils_hack here. It ships with setuptools, which has to
    # stay for pkg_resources, and site-packages/distutils-precedence.pth does
    # `import _distutils_hack` on every interpreter start. Removing one without
    # the other makes CPython print a traceback at every startup -- harmless,
    # but it lands in the language server's stderr and reads like a real error.
    site = libdir / "site-packages"
    for name in ("pip", "pip-*.dist-info"):
        for match in site.glob(name):
            shutil.rmtree(match, ignore_errors=True)

    # Defensive: if a .pth's target module is gone for any reason, drop the
    # .pth too rather than shipping a bundle that errors on every launch.
    hack_pth = site / "distutils-precedence.pth"
    if hack_pth.is_file() and not (site / "_distutils_hack").is_dir():
        hack_pth.unlink()

    shutil.rmtree(python_root / "share", ignore_errors=True)
    shutil.rmtree(python_root / "include", ignore_errors=True)


def precompile(py, python_root):
    """Compile every module to bytecode at build time.

    An earlier version of this script deleted __pycache__ to save space. That
    was a bad trade: importing bioservices from source costs ~5.3s, versus
    ~0.5s with cached bytecode, and antimony and libsbml add several more.
    Users paid roughly eight seconds of compilation on first launch to save a
    fraction of the download.

    Compiling here also makes the bundle work correctly if it ever lands
    somewhere read-only, where CPython could not write .pyc files at all and
    every single start would pay the full cost.
    """
    log("precompiling bytecode")
    # Returns non-zero for any file that fails to compile. Some third-party
    # packages ship intentionally broken or py2-only modules, so a failure here
    # is not fatal -- those modules simply stay uncompiled.
    subprocess.run(
        [str(py), "-m", "compileall", "-q", "-j", "0", str(python_root)],
        check=False,
    )


def dir_size(root):
    total = 0
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            total += path.stat().st_size
    return total


def package(python_root, platform):
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"antimony-runtime-{RUNTIME_VERSION}-{platform}.tar.gz"

    # Measured before packaging: this is what the extension's pre-flight disk
    # check needs, and guessing it wrong is how you get a failure halfway
    # through unpacking on a nearly full disk.
    unpacked = dir_size(python_root)

    log(f"packaging -> {out.name}")

    # Deterministic archive: identical inputs must produce identical bytes.
    #
    # By default `tarfile.open(mode="w:gz")` stamps the current time into the
    # gzip header and records each file's real mtime, uid and gid, so every
    # rebuild produced a different sha256 even with no source changes. That
    # meant re-running CI invalidated the checksums committed in runtime.ts and
    # forced a re-paste every time.
    #
    # Zeroing the timestamps and ownership, and walking the tree in sorted
    # order, makes the hash a function of the contents alone.
    def normalize(info):
        info.mtime = 0
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        return info

    def add_sorted(tf, path, arcname):
        tf.add(path, arcname=arcname, recursive=False, filter=normalize)
        if path.is_dir() and not path.is_symlink():
            for child in sorted(path.iterdir(), key=lambda c: c.name):
                add_sorted(tf, child, f"{arcname}/{child.name}")

    with open(out, "wb") as raw:
        # mtime=0 keeps the gzip header stable. filename="" is equally
        # important and much easier to miss: GzipFile otherwise records the
        # output file's own name in the header.
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                add_sorted(tf, python_root, "python")

    download = out.stat().st_size
    # Verify the archive round-trips. A truncated or partial tar is otherwise
    # indistinguishable from a good one until a user unpacks it.
    with tarfile.open(out) as tf:
        names = tf.getnames()
    expected = ["python/lib", "multiprocessing/queues.py", "site-packages"]
    for needle in expected:
        if not any(needle in n for n in names):
            raise SystemExit(f"archive is missing {needle!r} -- refusing to publish")
    log(f"archive verified ({len(names)} entries)")

    digest = hashlib.sha256(out.read_bytes()).hexdigest()

    (DIST / (out.name + ".sha256")).write_text(f"{digest}  {out.name}\n")

    # Paste this line straight into SIZES in src/runtime.ts.
    sizes_line = (
        f"  '{platform}': {{ download: {download}, unpacked: {unpacked} }},"
    )
    (DIST / f"sizes-{platform}.txt").write_text(sizes_line + "\n")

    log(f"sha256   {digest}")
    log(f"download {download / 1_048_576:.1f} MiB")
    log(f"unpacked {unpacked / 1_048_576:.1f} MiB")
    log(f"runtime.ts SIZES entry:\n{sizes_line}")
    return out, digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=sorted(PBS_TRIPLES))
    ap.add_argument("--skip-smoke-test", action="store_true")
    args = ap.parse_args()

    preflight()

    shutil.rmtree(BUILD, ignore_errors=True)
    BUILD.mkdir(parents=True)

    python_root = fetch_python(args.platform, BUILD)
    py = interpreter_path(python_root, args.platform)

    install_deps(py, args.platform)

    # The CI matrix runs each platform on a matching runner, so the smoke test
    # is a real execution. --skip-smoke-test exists only for local cross-builds.
    if not args.skip_smoke_test:
        try:
            smoke_test(py)
        except (OSError, subprocess.CalledProcessError) as exc:
            log(f"smoke test failed: {exc}")
            raise

    prune(python_root, args.platform)
    precompile(py, python_root)
    package(python_root, args.platform)
    log("done")


if __name__ == "__main__":
    main()