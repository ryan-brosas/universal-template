<!-- capsule-v2 -->
# Scrape loop + export — how does one loop serve eight platforms with per-platform delay budgets and timestamped CSVs?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What does the shared batch loop pin (delays, spinner lifecycle, logging hush) and what are the two CSV schema strategies?

## Per-platform delay ranges + transient spinner discipline + first-row vs union schemas
**Path/Symbol:** `scout.py:_get_delay_range` (:470-477), `_standard_scrape_loop` (:480-519), `_standard_export` (:522-537), platform call-sites (:564-734), `scrape_from_file` (:737-875).
**Signature:** `_standard_scrape_loop(scraper_func, items, label_prefix="@", delay_range=None) -> List[Dict]`; `_get_delay_range(fallback=(1.0, 2.5)) -> tuple`.
**Data Shape:** env-tunable `SCOUT_DELAY_MIN/MAX`, validated `(d_min, d_max) if d_max >= d_min >= 0 else fallback` (ValueError → fallback); per-platform overrides: instagram (1.5,4.0), tiktok (2.0,5.0), linkedin (3.0,6.0), github/twitch/linktree (0.5,1.5), youtube/pinterest (1.0,2.5).

### Decisive source
```python
# validation ladder: junk env values degrade to the safe default
return (d_min, d_max) if d_max >= d_min >= 0 else fallback

# inter-item delay ONLY between items:
if i < len(items):
    random_delay(*delay_range)

# strategy A (single-platform): first row is the schema
writer = csv.DictWriter(f, fieldnames=profiles[0].keys())

# strategy B (linkbio, heterogeneous rows): union of keys, sorted
all_keys = set()
for p in export_profiles: all_keys.update(p.keys())
writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
```

**Flow:** interactive paths collect identifiers → `_standard_scrape_loop` (spinner per item via transient Progress; success appends + renders a card AFTER `progress.stop()` so output isn't clobbered; RuntimeError breaks the batch per retry-semantics.md) → `_standard_export` (summary → enrichment prompt → CSV confirm). Bulk-from-file duplicates the loop inline with its own differences: no cards (one ✓ line each, follower count from `follower_count or subscribers`), NO enrichment, auto-export without asking.
**Invariant:** the delay fires only BETWEEN items (never after the last — no wasted tail sleep) and uses the platform's range because rate-limit tolerance differs by an order of magnitude (LinkedIn human-paced at 3–6s vs GitHub's API at 0.5–1.5s). The env override is global, not per-platform — settings-menu changes deliberately re-bias every platform. Spinner writes and result prints must be strictly sequenced around `progress.stop()` or Rich tears the layout. The two CSV strategies exist because strategy A silently drops columns absent from row 0 — acceptable within one platform's uniform dicts, wrong for linkbio's variable shape.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -cF "delay_range=(" scout.py` → **8** = def line :480 + seven per-platform budgets (:570,:581,:625,:636,:663,:674,:696,:733); `grep -n "fieldnames=" scout.py` pins both strategies (:532/:718/:863).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_standard_scrape_loop random_delay export csv", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-target delay budgets with validated env overrides and between-items-only spacing for any polite fan-out scraper; adapt budgets to your targets' tolerance; when exporting heterogeneous records always use the union-of-keys strategy — first-row schemas are the bug porters inherit silently.
