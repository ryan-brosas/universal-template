<!-- capsule-v2 -->
# executable-discovery-shortest-wins — how is a Chrome binary located, and which candidate wins?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** Given `browser="auto"`, what search order and tie-break selects the executable?

## exists+executable filter; shortest path beats first-found
**Path/Symbol:** `zendriver/core/config.py:find_executable` (:311-438) → `find_binary` (:288-308); `is_root` (:269-279); `temp_profile_dir` (:282-285).
**Signature:** `def find_executable(browser: BrowserType = "auto") -> PathLike`; `def find_binary(candidates: list[str]) -> str | None`.
**Data Shape:** BrowserType = `"chrome" | "brave" | "msedge" | "auto"`; auto tries chrome→brave→msedge, each building a per-OS candidate list (PATH sweep + platform app dirs); returns `os.path.normpath(winner)` or raises `FileNotFoundError`.

### Decisive source
```python
# find_binary
for candidate in candidates:
    if os.path.exists(candidate) and os.access(candidate, os.X_OK):
        rv.append(candidate)
winner = None
if rv and len(rv) > 1:
    # assuming the shortest path wins
    winner = min(rv, key=lambda x: len(x))
elif len(rv) == 1:
    winner = rv[0]
```

**Flow:** candidate lists are *ordered by preference* (e.g. chrome PATH sweep tries `google-chrome`, `chromium`, `chromium-browser`, `chrome`, `google-chrome-stable`), but the winner is **not** first-match — when several exist, the *shortest absolute path* wins (a deliberate proxy for "the canonical binary, not a versioned variant"). Linux Edge prefers wrapper scripts (`/opt/microsoft/msedge/microsoft-edge`) explicitly so user flags are respected (:377-389).
**Invariant:** the shortest-path tie-break can defeat an intentionally shimmed earlier PATH entry — on Arch, a `/bin/chromium` wrapper coexists with `/usr/sbin/chromium` and the shorter `/bin/...` wins even though it starts slower (observed live on this host). Porters relying on PATH precedence must not reuse this tie-break blindly.
**Probe:** static anchors at the pin: `grep -c 'def find_binary' zendriver/core/config.py` → 1; `find_executable("chrome")` resolves to `/bin/chromium` on the probe host (Arch, both chromium paths present) — behavior pinned to source lines :300-303.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "find_executable candidates", limit: 5 });
```

## Verdict
Adopt exists+X_OK filtering and normpath normalization; adapt the candidate tables to your distro; treat shortest-path-wins as optional — replace with first-match if your environment shims wrappers into PATH.
