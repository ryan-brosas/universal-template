<!-- capsule-v2 -->
# Settings live-config plane — how does a menu change take effect mid-session, and what do its validation ladders accept?

**Source:** Scout MIT `main@171503bf8c56d61fd6462ff08c557ec0b7fafa34`; Codebase Memory `Scout`. **Question:** What is the write path that makes `.env` edits behave live, and which validations guard each setting before it lands?

## Dual-write via `_update_env` + per-choice validation + asymmetric removal

**Path/Symbol:** `scout.py` — `settings_menu` (:878-1028), delay setter ladder (:996-1009), proxy removal (:988-994), proxy-file existence gate (:933-940), connection tester (:950-986), export cleanup (:1019-1028), `view_exports` (:1032-1056); consumer `_get_delay_range` (:470-477).

**Signature:** `_update_env(key, value)` (rewrites `.env` AND sets `os.environ[key]` in ONE call — owned by env-persistence.md); delay rule: `fmin < 0 or fmax < fmin ⇒ "✗ Invalid range"`, else persist both as `str(float)`.

**Data Shape:** keys touched by the menu: `SCOUT_PROXY`, `SCOUT_PROXY_FILE`, `SCOUT_FREE_PROXY` ('true'/'false'), `SCOUT_DELAY_MIN/MAX`, `LINKEDIN_COOKIE`; exports glob namespace `*_export_*.csv` shared with all writers (`{platform}_export_{YYYYmmdd_HHMMSS}.csv`).

### Decisive source

```python
# choice 6 — validate BEFORE persist; junk types caught separately:
fmin, fmax = float(new_min), float(new_max)
if fmin < 0 or fmax < fmin:
    console.print("[red]✗ Invalid range[/red]")
else:
    _update_env('SCOUT_DELAY_MIN', str(fmin))
    _update_env('SCOUT_DELAY_MAX', str(fmax))

# choice 5 — removal is TWO mechanisms, not one:
_update_env('SCOUT_PROXY', '')            # file gets empty value
_update_env('SCOUT_FREE_PROXY', 'false')  # boolean flipped, NOT deleted
_update_env('SCOUT_PROXY_FILE', '')
os.environ.pop('SCOUT_PROXY', None)       # process env actually cleaned
os.environ.pop('SCOUT_PROXY_FILE', None)
```

**Flow:** menu reads ALL current values from os.environ at ENTRY for display, mutates through `_update_env` per choice, then returns to the main loop; every consumer (`_get_delay_range`, `get_proxy`, LinkedIn's cookie gate) re-reads os.environ at USE time, so the next flow start reflects menu edits with no restart. The connection tester probes `https://httpbin.org/ip` with `verify=False`, scheme-prefixes bare `host:port` exactly like `get_httpx_proxy`, and on free-tier failure tries the first three fetched proxies at 8 s inside a `for/break` whose `else` prints "All free proxies failed" — advice fires only when nothing broke out.

**Invariant:** (1) EVERY mutation goes through `_update_env`; editing only `os.environ` would heal on restart while editing only the file never reaches the running process — the dual write IS the mid-session contract (and boot uses `setdefault`, so real-env wins over stale file lines). (2) The delay validator allows `min == max` (a legal fixed delay) but rejects inverted/negative ranges; non-numbers hit the ValueError branch ("Must be numbers") — validation happens at SET time so scrapers can trust `_get_delay_range`'s own fallback ladder to be almost dead code. (3) Removal deliberately mixes three shapes: empty-string for URL/file keys, literal `'false'` for the boolean flag (deleting it would let a stale `.env` line resurrect it on next boot), and `os.environ.pop` to keep exported environment clean for child processes. (4) Settings and exports share the working directory: cleanup globs the SAME `*_export_*.csv` pattern writers create, gated behind an explicit Confirm default=False; `view_exports` sorts that namespace by mtime desc and shows top-10 with a total-count line.

**Probe:** no upstream tests. Deterministic pins: `grep -n "_update_env(" scout.py | wc -l` → 11 call-site LINES (:930,:937,:944,:947,:989,:990,:991,:1005,:1006,:1016 plus def :143), zero raw `os.environ[` assignments outside `_update_env`'s own body :159; executable validation-predicate probe:

```
python3 - <<'EOF'
def accepts(fmin, fmax): return not (fmin < 0 or fmax < fmin)
assert accepts(1.0, 2.5) and accepts(2.0, 2.0)   # equal = fixed delay, legal
assert not accepts(2.5, 1.0) and not accepts(-1, 1)
EOF
```

**Retrieve:**

```ts
await mcp.codebase-memory.search_graph({ project: "Scout", query: "settings_menu _update_env delay proxy remove", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-at-set + dual-write-through-one-helper + re-read-at-use as the complete live-config pattern (~150 lines); adapt key names and validators; omit the httpbin tester if your targets forbid third-party echoes — the rest of the plane doesn't depend on it.
