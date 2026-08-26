<!-- capsule-v2 -->
# Update-check + install-mode update flow — how do you nag about upgrades once a day without breaking offline or unknown-version installs?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What caching and version-comparison rules make an agent-facing updater safe?

## 24h PyPI cache + pre-release-aware tuple + banner-once-per-day
**Path/Symbol:** `src/browser_harness/admin.py:_latest_release_tag/_version_tuple/check_for_update/print_update_banner/run_update` (:713-811, :1023-1075).
**Signature:** `_latest_release_tag(force=False)` caches `{tag, fetched_at}` in `<config>/version-cache.json` (chmod 600), TTL 24h, network failure falls back to last-known tag; `_version_tuple(v)` ranks `a < b < rc < final` via `(nums..., pre_rank, pre_num)`.
**Data Shape:** Banner gate `cache["banner_shown_on"] == today` ⇒ silent; `run_update(yes=False)`: git-mode refuses uncommitted trees and pulls `--ff-only`; pypi-mode runs `uv tool upgrade`; unknown mode refuses loudly; then pops the banner cache and offers daemon restart.

### Decisive source
```python
# Only short-circuit as "up to date" when we actually know the installed
# version. Otherwise `newer=False` just means "couldn't compare" — proceed.
if cur and latest and not newer:
    print(f"browser-harness is up to date ({cur}).")
    return 0
```

**Flow:** each script run: once-per-day stderr banner only when a NEWER version is known → --update compares → upgrade by install mode → invalidate banner cache → prompt-or--y daemon restart so new code loads on next call.
**Invariant:** "Unknown installed version" must NOT collapse to up-to-date (`cur or "(unknown)"` would parse as (0,) and flag every release newer — guarded in BOTH doctor and update); unreachable registry degrades to cached tag or silent no-op, never an error; git-mode never pulls over dirty worktrees.
**Probe:** No direct update-path unit test — coverage caveat; deterministic anchors verified at source :759-771 (cache+fallback), :774-784 (pre-release ranking), :969-971 (doctor's cur-guard comment), :1042-1051 (dirty-tree refusal). Adjacent pin: `tests/unit/test_admin.py:258-282` exercises run_doctor tolerating bad stored auth around these helpers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "update version cache banner", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt cache-with-fallback + explicit unknown-version handling + mode-split upgrade. Adapt registry endpoints and package-manager commands. Keep the banner-once-per-day gate — agents re-run CLIs constantly.
