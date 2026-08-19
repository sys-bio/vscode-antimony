# Developer instructions

## Setting up on a new device

```
cd vscode-antimony
npm install
npm run webpack
```

No virtual environment is needed any more. Press F5 to launch the Extension
Development Host; the extension downloads its own Python on first run.

Two things that will waste your time if you skip them:

* **Disable the published Antimony extensions** while developing. If
  `stevem.vscode-antimony` or the extension pack are installed from the
  Marketplace, they run alongside your development copy and their errors look
  like yours. Disable the pack first, since it will otherwise keep the
  extension enabled.
* **`npm run webpack` after every change.** `package.json` sets
  `"main": "./dist/extension.js"`, so VS Code runs the webpack bundle, not your
  `.ts` files. F5 rebuilds it via the `npm: webpack` task in `.vscode/tasks.json`.

---

## How the Python runtime works

The extension does not create a virtual environment. It downloads a prebuilt,
self-contained CPython 3.10 with every dependency already installed, and runs
the language server from it.

```
scripts/build_runtime.py   builds one tarball per platform (CI)
    |
    v
GitHub Release runtime-v<N>   holds the tarballs
    |
    v
src/runtime.ts   downloads, verifies the checksum, unpacks into globalStorage
```

Installed at
`~/Library/Application Support/Code/User/globalStorage/stevem.vscode-antimony/runtime/<N>/`
(equivalent paths on Windows and Linux). Uninstalling the extension removes it.

### Adding or changing a Python dependency

1. Edit `requirements-runtime.txt`. This is the only place pins live — CI tests
   against it too, so the tested stack and the shipped stack cannot drift.
2. Bump `RUNTIME_VERSION` in **both** `scripts/build_runtime.py` and
   `src/runtime.ts`. They must match; the build script refuses to run if they
   don't. Bumping is what makes existing users download the new bundle instead
   of keeping their old one.
3. Run the **Build Antimony runtime bundles** workflow (Actions tab, manual
   trigger). It builds and smoke-tests each platform and publishes a release.
4. Copy the `CHECKSUMS` and `SIZES` blocks from the **release job's** summary
   into `src/runtime.ts`. Use the release job, not the per-platform build
   summaries — only the release job reflects what was actually published.
5. Publish the extension.

Some pins cannot be raised without code changes. `requirements-runtime.txt`
explains each one; read the comments before bumping anything.

### Testing the runtime locally

To build a bundle without going through CI:

```
python3 scripts/build_runtime.py --platform darwin-arm64
```

Platforms: `win32-x64`, `darwin-arm64`, `linux-x64`. Build on a matching
machine — the wheels are native.

To run the extension against a local bundle instead of the published one, use
the **Run Extension (local runtime)** launch configuration, which sets
`ANTIMONY_RUNTIME_DIR`. `ANTIMONY_RUNTIME_TARBALL` also works and exercises the
real unpack path.

To test the download path as a user experiences it, delete the installed
runtime and launch normally:

```
rm -rf "$HOME/Library/Application Support/Code/User/globalStorage/stevem.vscode-antimony/runtime"
```

### Which interpreter is actually running

Guessing this wastes hours. Just look:

```
ps aux | grep "server/main.py" | grep -v grep
```

The path at the front of that line is the interpreter running the language
server. It should be under `globalStorage`. If it points anywhere else, the
`vscode-antimony.pythonInterpreter` setting is overriding it — clear it in
`settings.json`. Note that Settings Sync can restore it after you delete it.

---

## Packaging and publishing to the VS Code Marketplace

[Official docs](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)

```
npm install -g @vscode/vsce
```

1. Change the version (and publisher, if needed) in `package.json`.
2. `cd vscode-antimony`
3. **Comment out the logger code in `src/server/main.py`.** MUST DO BEFORE
   PUBLISHING.
4. Confirm the runtime release for the current `RUNTIME_VERSION` exists and
   `CHECKSUMS` holds real values for every platform you ship. A placeholder
   checksum now blocks installation on that platform rather than silently
   skipping verification.
5. `vsce package`
6. Install the resulting `.vsix` on a machine with no Python, no Git, and no
   old `vscode_antimony_virtual_env`. This is the only test that covers what
   users actually experience. A fresh OS user account works.
7. `vsce publish <version>`

**No `--target` needed.** Earlier releases were published per-platform
(`vsce publish --target win32-x64` and so on). The `.vsix` no longer contains
anything platform-specific — the Python is downloaded at runtime — so one
universal package covers every platform. Publishing per-target still works, but
it means one upload per platform for no benefit.

---

## Symlinks

`README.md` inside `vscode-antimony/` is a symlink to the repo root README.

Set up a symlink (Windows cmd):

```
git config core.symlinks true
mklink [Name of Symlink File] [Name of Source File]
```

Remove a symlink (Linux terminal):

```
cp --remove-destination `readlink [Name of Symlink File]` [Name of Symlink File]
readlink [Name of Symlink File]
```

If `readlink` still returns a path, the symlink is still active.

---

## Layout

```
.github/workflows/
  main.yml              tests, runs on push
  build-runtime.yml     builds runtime bundles, manual trigger only

vscode-antimony/
  requirements-runtime.txt   Python pins (runtime + CI)
  scripts/build_runtime.py   builds a platform bundle
  src/runtime.ts             download, verify, install, migrate
  src/extension.ts           activation, commands, language client
  src/server/                the Python language server
  runtime-dist/              build output (gitignored)
  runtime-build/             build scratch (gitignored)
  runtime-cache/             cached CPython downloads (gitignored)
```