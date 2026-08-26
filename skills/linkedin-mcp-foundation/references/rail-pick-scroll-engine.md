<!-- capsule-v2 -->
# Rail-pick scroll engine — how do you scroll an unknown SPA container until IT says it is done?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you exhaust a virtualized feed sidebar without assuming a result count or scrolling the wrong container?

## Pick the container by content, stop on growth-stall, budget from the caller's clock
**Path/Symbol:** `linkedin_mcp_server/core/utils.py:scroll_job_sidebar` (:174) + in-page JS `_RAIL_PICK_JS`; caller-side budget derivation `tools/job.py:121-147`.
**Signature:** `async def scroll_job_sidebar(page, settle_timeout=3.0, poll_interval=0.15, min_budget=0.4, max_scrolls=10, deadline=12.0) -> bool` — returns whether the evaluate RAISED (navigation destroyed the context), not whether cards were found.
**Data Shape:** The rail = the scrollable ancestor candidate holding the MOST DISTINCT job ids (so the detail pane's "similar jobs" module never wins). No target count: "how many cards a page yields belongs to LinkedIn."

### Decisive source
```text
Never wait on a zero timeout: Patchright reads 0 as NO timeout ("Pass `0`
to disable timeout"), so a spent budget would hang on a card-less page until
the tool is cancelled and EVERY page gathered so far is thrown away.
    await page.wait_for_selector(sel, timeout=max(1, min(5000, int(deadline*1000))))
First-card wait separately capped at 5s INSIDE the deadline — a page still
cardless after 5s is throttled/empty; waiting the full deadline would cost that
again on every one of max_pages navigations.

Stop rule: rounds end when the rail stops growing (id count OR scrollHeight);
a nothing-round waits once more at FULL settle_timeout before declaring
exhaustion — the fixed 0.5s single look cost a measured search 4 of its 11
cards. Later rounds start from 3x the previous batch time, floored at
min_budget. Round worst case = 2 * settle_timeout.

Re-render survival (in-page): the rail node is re-picked whenever document no
longer contains it — polling the old node measures "a corpse" until deadline;
adopting a replacement is NOT growth by itself (framework re-rendering the same
cards must not spend max_scrolls per render). A better pick displaces the first
when it holds MORE ids (the real rail may render late).

Tied-candidate rule: scroll only candidates tied with the pick that CONTAIN or
are contained by it — two tied SIBLINGS are the live shape, rail and detail
PANE; scrolling the pane loads its similar-jobs module into the document where
the caller reads those ids as search results (measured on a 6-to-6 tie: pane hit
31 ids, search returned 37 of which 31 were not results).

Navigation race: page.url still reports the OLD address ~6ms after the context
dies (measured over ten runs, 6ms min and max alike), and awaiting load state
returns instantly (previous document already loaded) — hence the raise-return
contract instead of URL sampling.

Caller budget coupling (tools/job.py): started=time.monotonic() BEFORE browser
work; extractor gets tool_timeout=max(0.0, tool_timeout - elapsed) — what is
LEFT of the figure FastMCP cancels the call on. A cold start spending 3 of 10
seconds left it planning against 8 it no longer had; the call was cancelled
with every page it had gathered.
```

**Flow:** wait for first card (bounded) → evaluate in-page engine → per round: re-collect candidates, pick by distinct-id count, scroll tied group, poll for growth with adaptive budgets → stall at full settle ⇒ done → return raise-flag.
**Invariant:** The engine trusts only growth signals measured off the live DOM — never assumed counts, never fixed sleeps, never stale nodes — and its wall-clock budget is derived from the CALLER's remaining cancellation budget, not a fresh constant.
**Probe:** `grep -c 'scroll_job_sidebar' linkedin_mcp_server/core/utils.py` → 1; `grep -cF 'min(5000, int(deadline * 1000))' linkedin_mcp_server/core/utils.py` → 1 (fixed-string: the needle's `(` `)` `*` are regex metachars); `grep -c 'tool_timeout=max(0.0, tool_timeout' linkedin_mcp_server/tools/job.py` → 1; DOM tests `tests/test_job_sidebar_scroll_dom.py` (696L), budget tests `tests/test_core_utils.py`, `tests/test_tools.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "scroll_job_sidebar rail pick deadline budget", limit: 5 });
```

## Verdict
Adopt content-scored container picking + growth-stall termination + caller-budget derivation for any infinite-scroll harvesting. Adapt selectors/id-heuristics to your target DOM. Omit LinkedIn job-card specifics.
