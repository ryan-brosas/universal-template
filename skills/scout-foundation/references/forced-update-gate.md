<!-- capsule-v2 -->
# Forced update gate — how does a hobby CLI hard-block old versions without blocking startup?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How do you check GitHub releases for a newer version at startup, keep the splash instant, and refuse to run when outdated?

## Background-thread check with one-shot cache and bounded join
**Path/Symbol:** `scout.py:_check_for_updates` (:87-123), `_start_update_check` (:126-131), `main` (:1060-1078).
**Signature:** `_check_for_updates() -> str | None`; `_start_update_check() -> threading.Thread`.
**Data Shape:** module-global `_update_cache = {"checked": False, "latest": None}` is the memo; releases API `GET api.github.com/repos/<owner>/<repo>/releases/latest`, `timeout=3`.

### Decisive source
```python
if _update_cache["checked"]:
    return _update_cache["latest"]
_update_cache["checked"] = True          # set BEFORE the network call
...
def _ver(s):
    try:
        return tuple(int(x) for x in s.split("."))
    except (ValueError, AttributeError):
        return (0,)
if _ver(latest) > _ver(__version__):
    _update_cache["latest"] = latest

# main()
_update_thread = _start_update_check()
console.clear()
_update_thread.join(timeout=3.0)         # never wait more than 3s
...
if latest:
    ...Panel("Update Required")...
    sys.exit(1)
```

**Flow:** spawn daemon thread at `main()` entry → clear screen immediately → join with `timeout=3.0` so a hung API costs ≤3s → read the cache; a newer tag renders an "Update Required" panel naming `git pull origin main` and exits `sys.exit(1)`; equal/older versions fall through to the menu loop.
**Invariant:** the `checked` flag flips before any network I/O so concurrent callers can't stampede; every failure mode (non-200, missing tag, unparsable version, any Exception) degrades to `latest=None` — the gate may only ever *under*-notify, never block on error. Unparsable versions compare as `(0,)` which never triggers the gate.
**Probe:** no direct test exists (repo ships zero tests — global caveat). Deterministic probe: `grep -n "_update_cache" scout.py` pins the three touchpoints (:84, :89-92, :1066); graph retrieval resolves `Scout.scout._check_for_updates`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_check_for_updates update_cache", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the daemon-thread + bounded-join + cached-once + fail-silent shape and the tuple-split semver compare; adapt the repo slug, panel copy, and whether outdatedness is fatal (`sys.exit(1)` here) to your release policy; omit the ASCII-gradient splash around it (product surface). Coverage caveat: behavior pinned by source lines only, no test runner exists upstream.
