<!-- capsule-v2 -->
# Browser-launch flag assembly — which flags are stealth-critical, which are cargo cult, and how do you build a per-browser arg list that is both sorted and conflict-free?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** what is the correct flag set and assembly order for launching a stealth Chrome, and which "stealth" flags are actually anti-stealth?

## Sorted dedup assembly + guarded add_argument + root auto-sandbox-drop
**Path/Symbol:** `zendriver/core/config.py:Config` (:29-266), `find_executable` (:311-438), `find_binary` (:288-308); launch in `core/browser.py:start` (:314-436).
**Signature:** `Config.__call__() -> list[str]`; `Config.add_argument(arg)`; `Config.browser_args` property returns `sorted(defaults + custom)`.
**Data Shape:** default flag block (:119-137): `--remote-allow-origins=*`, `--no-first-run`, `--no-service-autorun`, `--no-default-browser-check`, `--homepage=about:blank`, `--no-pings`, `--password-store=basic`, `--disable-infobars`, `--disable-breakpad`, `--disable-component-update`, `--disable-backgrounding-occluded-windows`, `--disable-renderer-backgrounding`, `--disable-background-networking`, `--disable-dev-shm-usage`, `--disable-features=IsolateOrigins,DisableLoadExtensionCommandLineSwitch,site-per-process`, `--disable-session-crashed-bubble`, `--disable-search-engine-choice-screen`.

### Decisive source
```python
def add_argument(self, arg):
    if any(x in arg.lower() for x in ["headless","data-dir","data_dir","no-sandbox","no_sandbox","lang"]):
        raise ValueError('"%s" not allowed. please use one of the attributes of the Config object to set it' % arg)
    self._browser_args.append(arg)
# __call__ dedups custom against defaults:
if self._browser_args:
    args.extend([arg for arg in self._browser_args if arg not in args])
# root detection auto-drops sandbox:
if is_posix and is_root() and sandbox:
    self.sandbox = False   # else Chrome refuses to start as root
```

**Flow:** `Config.__call__()` copies defaults, appends `--user-data-dir`, forces the two `--disable-features`/`--disable-session-crashed-bubble` again (idempotent), adds expert/headless/UA/no-sandbox/host/port/webrtc/webgl flags, then extends with custom args that aren't already present. `browser_args` (property) returns the SORTED union — deterministic ordering. `add_argument` REJECTS anything that should be set via a typed attribute (headless/data-dir/sandbox/lang), forcing the safe path. `find_executable` probes PATH + platform defaults and picks the **shortest existing executable path** when multiple candidates match (`min(rv, key=len)`), preferring Linux msedge wrapper scripts over raw binaries.
**Invariant:** the flag list is deterministic (sorted) and conflict-free (dedup); stealth-critical flags are `--disable-blink-features`-style anti-detection + the `--remote-allow-origins=*` (needed for modern CDP) — while this repo does NOT ship `--enable-automation` (the anti-stealth NEGATIVE, same as the linkedin-profile-scraper-api puppeteer-flag-stack finding). The `--user-data-dir` is lazily created (temp profile) so a Config can be REUSED as a template across multiple browser instances.
**Probe:** deterministic pins (no unit test — coverage caveat; all paths anchored at the `zendriver/` package dir `<inspo>/external/zendriver/zendriver`): `grep -n 'shortest path wins' core/config.py` → :302; `grep -n 'Pick the wrapper scripts first' core/config.py` → :379; `grep -n 'not allowed. please use one of the attributes' core/config.py` → :244. Cross-reference: linkedin-profile-scraper-api puppeteer-flag-stack (container quartet + `---single-process` triple-dash no-op) — zendriver is the flag-set counterpart.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "Config browser_args add_argument find_executable", limit: 5 });
```

## Verdict
Adopt: typed-attribute config with guarded add_argument, sorted dedup assembly, shortest-path binary resolution, and root auto-sandbox-drop. Adapt flag names to the Chrome version you pin (re-verify quarterly). Omit the expert-mode debug flags for production. Coverage: source-pinned only.
