<!-- capsule-v2 -->
# Logging hush ladder — how does a Rich TUI silence chatty scraper libraries without owning their logging config?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What are the two quiet-by-default mechanisms, and what breaks if one restore path is missed?

## Two-layer quiet default: boot floor + per-call root CRITICAL walls
**Path/Symbol:** `scout.py:_verbose` (:19), `logging.basicConfig` (:20-23); hush walls in `_standard_scrape_loop` (:490-495 save/raise/call/restore-success, :505-506 RuntimeError restore, :511-512 Exception restore) and `scrape_from_file` (:829-834 wall + success restore, :847-848 exception restore); noise sources: `logger = logging.getLogger(__name__)` in ALL TEN scraper/enrichment modules (`app/scrapers/stealth.py:9`, tiktok:12, linkedin:13, enrichment:15, github:21, youtube:21, twitch:21, pinterest:22, instagram:22, linktree:27).
**Signature:** module global `_verbose: bool = '--verbose' in sys.argv or '-V' in sys.argv`; wall pattern `prev_level = logging.getLogger().level` → `if not _verbose: logging.getLogger().setLevel(logging.CRITICAL)` → `scraper_func(item)` → `setLevel(prev_level)`.
**Data Shape:** boot floor WARNING (`DEBUG` under -V); per-call ceiling CRITICAL; exactly 2 raise sites (:492, :831) and 5 restore sites (:495 success, :506 RuntimeError, :512 Exception, :834 success, :848 exception).

### Decisive source
```python
# scout.py — every item wraps the scraper in a save/hush/restore wall
prev_level = logging.getLogger().level
if not _verbose:
    logging.getLogger().setLevel(logging.CRITICAL)
profile = scraper_func(item)
if not _verbose:
    logging.getLogger().setLevel(prev_level)     # success path
...
except RuntimeError as e:
    if not _verbose:
        logging.getLogger().setLevel(prev_level) # escalation path
...
except Exception as e:
    if not _verbose:
        logging.getLogger().setLevel(prev_level) # swallow path
```

**Flow:** `-V/--verbose` sets `_verbose` before anything else runs (and is stripped from `_args` at :25 so version/help matching never sees it — see `interactive-shell`) → `basicConfig` floors the root logger at WARNING (DEBUG when verbose) → inside EACH loop item, root level is saved, raised to CRITICAL around the scraper call, and restored on all three exits. The ten module loggers never configure a level of their own.
**Invariant:** module loggers created with `getLogger(__name__)` and NO explicit level inherit their effective level from ROOT — that is why one `setLevel` on `logging.getLogger()` (the root) gates all ten modules at once, and also why any future module that calls `logger.setLevel(...)` would punch a hole through the hush invisible to this code. A missed restore path leaves the entire console silent for the rest of the session (subsequent warnings/errors never surface), which is why restores are duplicated per exit rather than centralized. With `-V`, both walls are skipped entirely: scraper DEBUG output flows to the console for diagnosis.
**Probe:** zero-test repo; deterministic probes EXECUTED this pass at pin via grep tool: pattern `_verbose|setLevel|basicConfig` over scout.py → exactly **17 matches** at lines {19,20,21,491,492,494,495,505,506,511,512,830,831,833,834,847,848} (def + config + 14 wall/restore lines); pattern `= logging\.getLogger\(__name__\)` over app/scrapers/**.py → exactly **10 files** (one logger per module, none with a following `setLevel`).
**Coverage:** `check_index_coverage(scout.py, app/scrapers/stealth.py)` → `no_recorded_issue` / `metadata_match` @ generation 2026-08-19T03:21:19Z (best-effort signal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", name_pattern: "^_verbose$", fields: ["lines"] });
```
Resolves rank-1 to `Scout.scout._verbose` Variable scout.py:19.

## Verdict
Adopt the two-layer shape for any console TUI wrapping chatty third-party clients: a coarse boot floor plus narrow per-call hush walls with restore-on-every-exit; adapt floor/ceiling levels to your library's verbosity. Omit per-module logger levels unless you rework the hush to target named loggers — they silently defeat a root-level wall.
