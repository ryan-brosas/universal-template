<!-- capsule-v2 -->
# pydevd remote egg version stamp — which artifact carries the debugger build identity for remote attach?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** How does a remote interpreter prove it runs the SAME debugger train as the IDE?

## Install tree keeps @@BUILD_NUMBER@@ placeholder; the distributable egg is stamped
**Path/Symbol:** `debug-eggs/pydevd-pycharm.egg` (38 MB zip) vs `plugins/python-ce/helpers/pydev/_pydevd_bundle/pydevd_comm.py`:154.
**Signature:** wrapper `pydevd_pycharm.py` (11 lines): re-exports settrace/stoptrace; __version__ = VERSION_STRING.
**Data Shape:** egg contains the full pydevd tree incl. pydevd.py, pydevd_pycharm.py, _pydevd_bundle/pydevd_comm.py.

### Decisive source
```
install copy:  VERSION_STRING = "@@BUILD_NUMBER@@"   # loose staged source keeps token
egg copy:      VERSION_STRING = "PY-262.9437.214"    # distributable stamped productCode+buildNumber
```

(measured byte-for-byte from this install, 2026-08-25.)

**Flow:** IDE pip-installs the egg into the remote interpreter (or user installs manually) → client imports pydevd_pycharm → __version__ reports the STAMPED train → during connect the version rides the CMD_VERSION handshake so the IDE can warn on mismatch. The loose install tree never gets stamped because it is staging material, not the shipped-to-python artifact.
**Invariant:** Version identity lives in the DISTRIBUTABLE artifact, not the staging tree; the 11-line wrapper is the whole public API (settrace, stoptrace, __version__). Egg-dir deployments also skip cython extension imports entirely (speedup-ladder carve-out).
**Probe:** executed 2026-08-25 via zipfile listing — PASS egg carries pydevd.py, PASS egg carries pydevd_pycharm.py wrapper; VERSION_STRING contrast printed above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev.pydevd.settrace" });
// -> Function pydevd.settrace @ plugins/python-ce/helpers/pydev/pydevd.py:1810 — EXECUTED (the API the egg re-exports)
```

## Verdict
Adopt stamp-the-artifact versioning (placeholder stays in staging; distributables carry product+build). Adapt stamp format. Omit remote-debug transport specifics — they live server-side.