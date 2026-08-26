<!-- capsule-v2 -->
# Bounded element-read budget — how do you bound the WALL-CLOCK damage one malformed or virtualized card can inflict in a DOM sweep?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file in tree — README carries only a bare "MIT License" mention; treated pattern-only) `main@e294ac09c9b9`; Codebase Memory `hassan-sales-nav-profiles-scraper` (coverage `no_recorded_issue`+`metadata_match`). **Question:** the per-row exception island stops one bad card from crashing the sweep — what stops one bad card from STALLING it?

## two-tier waits: generous page gates, 1 s per-element reads, total-value coercion
**Path/Symbol:** `linkedin_scraper.py:main` inner row loop (:175–224) — five per-element read sites (:178/:183/:207/:211/:214), all `timeout=1000`; page-level waits stay an order of magnitude looser by design (:149 anchor gate 20 000 ms, :156 container wait 10 000 ms).
**Signature:** `element.get_attribute('href', timeout=1000) or ""`; `ancestor_div.get_attribute('data-scroll-into-view', timeout=1000) or ""`; `name_loc.first.inner_text(timeout=1000).strip()`.
**Data Shape:** attribute reads coerce to `""` on timeout (`or ""`) so the value is TOTAL; text reads strip and may return empty; every read either succeeds fast, returns its default at ≤1 s, or raises into the surrounding island.

### Decisive source
```python
href = element.get_attribute('href', timeout=1000) or ""            # identity input #1: capped + total
try:
    ancestor_div = element.locator('xpath=ancestor::div[@data-scroll-into-view]').first
    if ancestor_div.count() > 0:
        urn = ancestor_div.get_attribute('data-scroll-into-view', timeout=1000) or ""
...
name = name_loc.first.inner_text(timeout=1000).strip()               # name fallbacks share the same cap
```

**Flow:** per card the sweep performs at most FOUR wire-bound reads (anchor href :178 → row URN attribute :183 → one container-or-element-scoped name span read :207 XOR :211 → whole-element text :214 only when both span scopes came up empty). Each is budgeted at exactly 1 s, so a fully-stuck card costs ≈4–5 s worst case, then the island continues to card i+1.
**Invariant:** latency isolation is a DIFFERENT axis than failure isolation: the try/except island bounds WHICH code runs after a fault; the 1 s budgets bound HOW LONG any single DOM read may hang before it. A framework-default action timeout (Playwright's 30 s) applied to one detached/virtualized element would stall ~30 s PER READ × up to four reads — minutes per bad page. The `or ""` keeps values total so the identity ladder advances to its next rung instead of aborting the row; budgets make the abort path FAST.
**Probe:** repo has no tests — coverage caveat recorded (source-grounded). Executed this pass: grep `timeout=1000` ⇒ exactly :178/:183/:207/:211/:214 (the ONLY other timeout literals are page-level :149 `timeout=20000`, :156 `timeout=10000`); grep `or ""` ⇒ exactly :178/:183; pass-1 py_compile exit-0 and utf-8 RED/GREEN stand unchanged (tree byte-identical at the same pin HEAD).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", name_pattern: "^main$", fields: ["lines"] });
// ⇒ resolves hassan-sales-nav-profiles-scraper.linkedin_scraper.main Function :33–259 (executed this pass:
// 1 code row + branch node). Name-only 47-node graph — body literals are not nodes; the byte-exact
// greps above are the standing source-read evidence.
```

## Verdict
Adopt two-tier wait budgeting for ANY DOM sweep over lazy/virtualized lists: generous page-level readiness gates, stingy ≈1 s per-element reads, total-value coercion so extraction ladders continue past dead elements; adapt budgets to host-framework defaults (Selenium implicit/explicit waits split differently) and drop the coercion where absence SHOULD raise loudly. Omit nothing structural. Contrast: scrape-orchestration-template's islanded getters degrade VALUES while this seam degrades TIME — compose both so one bad card neither crashes nor stalls the sweep; na-preserving-row-extraction is the schema-total sibling at the row level; url-roundtrip-extraction shows the islands-alone variant whose reads ride library defaults.
