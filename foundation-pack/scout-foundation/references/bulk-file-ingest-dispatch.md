<!-- capsule-v2 -->
# Bulk file ingest + dispatch — how does bulk-from-file mode turn a messy username list into scraper calls, and where does it deliberately diverge from the interactive contract?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What does `scrape_from_file` re-implement rather than reuse, and which three divergences must a porter choose between consciously?

## Tolerant ingest ladder → own platform menu → per-platform dispatch → flattened error contract
**Path/Symbol:** `scout.py:scrape_from_file` (:737-875): ingest ladder (:744-758), empty guard (:760-762), bulk platform menu (:767-778) with its own `platform_map` (:780-790), per-platform lazy dispatch (:792-811), LinkedIn cookie re-gate (:797-800, owned by `prerequisite-gates`), Continue gate (:816), inline loop (:824-853, RuntimeError flattened at :846-850), unconditional export tail (:857-870 — the no-enrichment/auto-export asymmetry sentence is owned by `scrape-loop-export`).
**Signature:** `scrape_from_file() -> None`; prompts filename (default `usernames.txt`) and platform choice; exports `<platform_key>_export_<timestamp>.csv`.
**Data Shape:** `.txt` = non-empty lines, stripped, `@` removed; `.csv` = DictReader column fallback chain `username → Username → handle → Handle`, else first column of the row; result `usernames: list[str]`.

### Decisive source
```python
# :749 the CSV column ladder; :758 the txt comprehension
username = row.get('username', '') or row.get('Username', '') or row.get('handle', '') or row.get('Handle', '')
...
usernames = [line.strip().replace('@', '') for line in f if line.strip()]

# :784 vs show_menu :412-413 — positions 4/5 are SWAPPED between the two menus
"4": ("youtube", "YouTube"),
"5": ("github", "GitHub"),

# :809 bulk pins ONE linktree host; interactive imports BOTH + first-hit scrape_all (:679)
from app.scrapers.linktree import scrape_linktree as scraper_func

# :846-850 bulk has NO RuntimeError escalation — every exception is a per-item ✗
except Exception as e:
    if not _verbose:
        logging.getLogger().setLevel(prev_level)
    progress.stop()
    console.print(f"  [red]✗[/red] [dim]@{username}[/dim]")
```

**Flow:** prompt file → parse by extension (CSV ladder / txt strip) → guard empty → platform re-selection from the BULK map → lazy-import that platform's single scraper as `scraper_func` → Confirm "Continue?" → inline loop with transient spinner, `_verbose` hush walls (see `logging-hush-ladder`), follower/subscribers fallback line (:839) → auto-export first-row-schema CSV when anything succeeded.
**Invariant:** bulk mode is a PARALLEL pipeline, not a parameterization of `_collect_usernames`/`_standard_scrape_loop`/`_standard_export`; three divergences are decisions, not accidents: (a) input tolerance lives only here — the column ladder plus @-stripping exists so exported lists round-trip back in; (b) linkbio first-hit multi-host probing (`scrape_all`) is OFF in bulk — you commit to one host up front (:809), while the interactive flow probes all four hosts (:679); (c) the typed retry contract (`RuntimeError` = fatal batch break) has EXACTLY ONE consumer — the interactive shared loop (:504-509); bulk flattens rate-limit errors into per-item ✗ continues. Upstream also lets the two menus disagree about whether slot 4 is GitHub or YouTube — normalize this when porting rather than copying either order blindly.
**Probe:** zero-test repo; deterministic probes EXECUTED this pass at pin via grep tool over scout.py: pattern `endswith\('\.csv'\)|or row\.get|replace\('@', ''\)|platform_map|import scrape_linktree|Confirm\.ask\("Continue\?"` → exactly **10 matches**: {:552 collect-usernames' own @-strip (cross-ref), :679 interactive dual import, :745 csv test, :749 column ladder, :753/:758 bulk strips, :780/:790 map def+lookup, :809 bulk single-host import, :816 continue gate}. Graph control: `trace_path` inbound on `Scout.scout._standard_export` shows the seven standard flows at hop 1 and main at hop 2 with NO `scrape_from_file` caller row — bulk never reaches the shared export/enrichment plane.
**Coverage:** scout.py `no_recorded_issue`/`metadata_match` @ generation 2026-08-19T03:21:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "scrape_from_file usernames csv platform", limit: 5 });
```
Resolves rank-1 to `Scout.scout.scrape_from_file` Function scout.py:737.

## Verdict
Adopt the tolerant ingest ladder (extension-aware parse + case-variant column fallback + first-column rescue + @ normalization) for any bulk CLI fed by exported lists; adapt column names to your ecosystem. Treat the three divergences as explicit choices: keep multi-host probing where identity is ambiguous, keep exactly ONE consumer for your fatal-error contract, and unify menu orders across entry paths instead of inheriting upstream's inconsistency.
