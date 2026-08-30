<!-- capsule-v2 -->
# Update-check + install-mode update flow — how do you nag about upgrades once a day without breaking offline or unknown-version installs, and how does an operator opt out entirely?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** What caching, version-comparison, and opt-out rules make an agent-facing updater safe?

## 24h PyPI cache + pre-release-aware tuple + banner-once-per-day + env kill switch
**Path/Symbol:** `src/browser_harness/admin.py`: `_latest_release_tag` (:844-856), `_version_tuple` (:859-869), `check_for_update` (:872-877), `print_update_banner` (:880-895; kill switch :883-884), `run_update` (:1139-1191).
**Signature:** `_latest_release_tag(force=False)` caches `{tag, fetched_at}` in `<config>/version-cache.json` (chmod 600), TTL 24h, network failure falls back to last-known tag; `_version_tuple(v)` ranks `a < b < rc < final` via `(nums..., pre_rank, pre_num)`.
**Data Shape:** Banner gate order: kill-switch env → daily cache gate → network compare → print+record. `run_update(yes=False)`: git-mode refuses uncommitted trees and pulls `--ff-only`; pypi-mode runs `uv tool upgrade`; unknown mode refuses loudly; then pops the banner cache and offers daemon restart.

### Decisive source
```python
def print_update_banner(out=None):
    """Print the update banner to stderr once per day. Silent when up-to-date or offline."""
    import sys
    if os.environ.get("BH_UPDATE_CHECK", "").strip().lower() in {"0", "false", "no", "off"}:
        return
    out = out or sys.stderr
    cache = _cache_read()
    today = time.strftime("%Y-%m-%d")
    if cache.get("banner_shown_on") == today:
        return
```

**Flow:** each script run: `BH_UPDATE_CHECK ∈ {0,false,no,off}` (strip+lowered) short-circuits BEFORE any cache read or network call → otherwise once-per-day stderr banner only when a NEWER version is known → --update compares → upgrade by install mode → invalidate banner cache → prompt-or--y daemon restart so new code loads on next call.
**Invariant:** The kill switch must precede side effects (an operator disabling update checks on an air-gapped box must not still pay a cache write or DNS attempt). "Unknown installed version" must NOT collapse to up-to-date (`cur or "(unknown)"` would parse as (0,) and flag every release newer — guarded in BOTH doctor and update); unreachable registry degrades to cached tag or silent no-op, never an error; git-mode never pulls over dirty worktrees.
**Probe:** `tests/unit/test_admin.py::test_update_banner_can_be_disabled_without_network_or_cache_access` (:23-29, parametrized `"0"/"false"/"NO"/" off "` with `_cache_read` and `check_for_update` monkeypatched to `pytest.fail`) and `::test_update_banner_remains_enabled_by_default` (:32-45). Remaining caveat: the deeper update path (dirty-tree refusal, mode split) has no direct unit test — deterministic anchors verified at source :1139-1191.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "update version cache banner", limit: 10, fields: ["signature", "file"] });
```
Resolves the family at post-drift positions (verified live this pass).

## Verdict
Adopt cache-with-fallback + explicit unknown-version handling + mode-split upgrade + a kill switch ordered before ALL side effects. Adapt registry endpoints, package-manager commands, and env name. Keep the banner-once-per-day gate — agents re-run CLIs constantly.
