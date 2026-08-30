<!-- capsule-v2 -->
# Session stats render side effect — where should a CLI count "processed this session", and what silently miscounts when the counter rides on presentation?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** Why does Scout's header "Scraped: N this session" stay at 0 after a full bulk run that filled a CSV?

## One-key session counter whose ONLY write lives inside a render helper
**Path/Symbol:** `scout.py:_session_stats` (:83, module global); sole increment `_profile_card` :259 (`_session_stats["scraped"] += 1`); sole `_profile_card` call site `_standard_scrape_loop` :500 (after `progress.stop()`, success branch only); displays `show_header` :397-398 (gated `> 0`) and `settings_menu` :899 (unconditional).
**Signature:** `_session_stats = {"scraped": 0}`; no reset site anywhere in scout.py — process-lifetime accumulator.
**Data Shape:** single-key dict; incremented once per rendered profile card; bulk mode never renders cards.

### Decisive source
```python
# scout.py :83 / :259 / :500 — write point is INSIDE the card renderer
_session_stats = {"scraped": 0}
...
def _profile_card(profile: dict):
    """Display a scraped profile as a compact card."""
    _session_stats["scraped"] += 1          # side effect of presentation
...
                if profile:
                    profiles.append(profile)
                    progress.stop()
                    _profile_card(profile)   # interactive loop renders cards…
# ...while bulk mode prints ✓ lines instead (scrape_from_file :841):
console.print(f"  [green]✓[/green] @{username}  [dim]{follower_count:,} followers[/dim]")
```

**Flow:** interactive path → shared loop success → card rendered → counter advances → later re-renders of `show_header` show it once > 0, settings menu shows it always ("0 this session" otherwise). Bulk path → per-item ✓ line → no card → no increment → CSV still fills, counter stays 0.
**Invariant:** the counter measures PRESENTATION events, not data events: it equals "cards drawn", which happens to equal "interactive successes" only because exactly one call site exists (:500). Any acquisition path that skips cards (bulk), any future caller of `_profile_card` for non-scrape rendering, or any refactor that stops rendering on success all decouple the number from reality without touching the counter. The leaf's own Boundaries section historically called `_profile_card` "cosmetic… no porting contract" — this side effect is precisely the porting contract it hid.
**Probe:** zero-test repo; deterministic probes EXECUTED this pass at pin via grep tool: pattern `_session_stats|_profile_card\(` over scout.py → exactly **7 matches** at lines {83 def, 257 def-card, 259 increment, 397+398 header read pair, 500 sole call site, 899 menu read}; the increment list contains exactly one `+=` site (:259). Graph control: `query_graph` USAGE/WRITES edges from `_session_stats` → {_profile_card :257, show_header :370, settings_menu :878} + module WRITES artifact (the augmented assignment inside :259).
**Coverage:** scout.py `no_recorded_issue`/`metadata_match` @ generation 2026-08-19T03:21:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", name_pattern: "^_session_stats$", fields: ["lines"] });
```
Resolves rank-1 to `Scout.scout._session_stats` Variable scout.py:83.

## Verdict
Adopt session/activity counters attached to DATA events (the append-to-results site), not to render helpers; adapt display gating freely. Omit render-side-effect counting in any port — it is the defect-shaped lesson here, kept visible because the miscount is silent (bulk runs report "0 scraped" while exporting every row).
