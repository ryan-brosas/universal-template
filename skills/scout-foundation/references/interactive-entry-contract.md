<!-- capsule-v2 -->
# Interactive entry contract — what must every platform flow do before, during, and after the loop?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What is the fixed shape of a `scrape_<platform>_interactive` function, and where do platforms deliberately break it?

## header → collect → empty-guard → loop → export; LinkedIn's bespoke input + linkbio's inline export
**Path/Symbol:** `scout.py:_collect_usernames` (:540-561); `scrape_instagram_interactive` (:564-571), `scrape_tiktok_interactive` (:574-582), `scrape_linkedin_interactive` (:585-626), `scrape_github_interactive` (:629-637), `scrape_youtube_interactive` (:640-664), `scrape_twitch_interactive` (:667-675), `scrape_linktree_interactive` (:678-723), `scrape_pinterest_interactive` (:726-734).
**Signature:** `_collect_usernames(platform_name, prompt_label="Username", strip_at=False) -> List[str]`; every interactive fn returns None (all output via console / files).
**Data Shape:** collection loop: `Prompt.ask(label, default="")`, empty line terminates, blanks skipped, live ✓ echo per item; per-platform knobs: strip_at=True for instagram/tiktok, label "Username/URL" for linkedin, "Channel" for youtube; delay ranges differ up to 12× (see `scrape-loop-export`).

### Decisive source
```python
# the shared collector — note @-stripping happens INSIDE the loop (per-entry),
# and echo mirrors what was stored:
if strip_at:
    entry = entry.replace('@', '')
entry = entry.strip()
if entry:
    items.append(entry)
    prefix = "@" if strip_at else ""
    console.print(f"[green]✓[/green] Added {prefix}{entry}")

# LinkedIn BREAKS the abstraction for URL paste-tolerance:
entry = entry.strip().rstrip('/')
if '/in/' in entry:
    entry = entry.split('/in/')[-1]
entry = entry.lstrip('@').strip()
```

**Flow:** `_platform_header` → optional lazy import → prerequisite gate (LinkedIn only, duplicated at bulk :797-800 per `prerequisite-gates`) → collect usernames (shared helper or bespoke loop) → empty-guard return → `_standard_scrape_loop(scraper, items, label_prefix, delay_range)` → export. Two deviations: linktree runs its own sub-menu mapping choice→(scraper, platform_name) then exports INLINE with union-schema flattening (`social_*` columns, sorted fieldnames — NOT `_standard_export`'s first-row schema); YouTube collects handles-or-channel-IDs verbatim (no normalization at all).
**Invariant:** the contract is positional, not structural — every flow must (1) refuse-before-render when prerequisites are missing, (2) survive zero input with a friendly return, (3) route through the ONE shared loop so logging-hush/spinner/delay semantics stay uniform. A porter adding a platform inherits the contract by calling the same helpers; bypassing `_standard_scrape_loop` (as linktree's export does, not its scrape) is the sanctioned escape hatch ONLY for post-loop shape changes.
**Probe:** no tests (zero-test repo). Deterministic probe: `grep -n "_standard_scrape_loop(" scout.py` → exactly 8 call sites (:570,:581,:625,:636,:663,:674,:696,:733), one per interactive flow incl. linktree; `grep -n "_collect_usernames(" scout.py` → 6 users (linkedin/youtube bespoke); `grep -cn "strip_at=True" scout.py` = 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_collect_usernames interactive scrape platform", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-phase flow template and single-collector discipline for any multi-source CLI fan-out; adapt labels/normalization per input dialect (URLs vs handles vs channel IDs); omit nothing — but preserve the two sanctioned deviations (LinkedIn's `/in/` splitter, linktree's union-schema export) as documented exceptions, not patterns to generalize.
