<!-- capsule-v2 -->
# Cross-frame reads & waits: aria-ref handles reach iframes; appearing races, disappearing gathers

## Source / Question
`pydantic_ai_harness/playwright/_toolset.py:1622–1672, 2302–2401` @ `main@f971198` — Page-level Playwright calls stop at the frame boundary, so embedded schedules/checkout/chat widgets are invisible to `inner_text` and matched by nothing in waits. How do you read and wait across frames without letting one unresponsive embed eat the deadline?

## Path / Symbol
`playwright/_toolset.py` — `_frame_text` sweep (:1622–1648), `_page_text` (:1650–1660), `_frame_budget` (:1662–1672), `wait_for` text-engine escaping (:2328–2345), `_wait_in_any_frame` dual-direction strategy (:2354–2401). Vendor-fact ledger = module docstring (:1–99, dated re-verify protocol pinned to playwright>=1.61.0).

## Signature
```python
_FRAME_TEXT_BUDGET_MS = 2_000      # ONE budget for the whole sweep, not per frame
def _frame_budget(self, timeout_ms):
    if timeout_ms in (None, 0): return _FRAME_TEXT_BUDGET_MS
    return min(timeout_ms, _FRAME_TEXT_BUDGET_MS)
async def _wait_in_any_frame(self, page, query, timeout_ms, *, gone: bool) -> None
```

## Data Shape
Frame texts render as `[frame <sanitized-url>]\n<text>` blocks appended after main-frame text; failures skipped (a detaching frame must not fail a successful action). Snapshot refs look like `f1e4` inside embeds and resolve via the driver's frame jump — plain CSS cannot cross.

### Decisive source
Appear vs disappear asymmetry (:2360–2367): "Appearing is a race: every frame is watched at once and the first match wins… Disappearing has to hold everywhere at once, so those are awaited together — a frame that never contained the element reports it hidden immediately [wait_for_selector state='hidden' satisfied by hidden OR absent], and a race would settle on that frame before the one that does contain it has let go." Appear path reads EVERY finished task before returning (:2383–2397) "including when an earlier one in the same batch already matched: an exception nobody retrieves surfaces later, out of context, as an unhandled task error." Text-wait escaping (:2332–2337): interpolate quoted inside `:text("…")` rather than after `text=` where a `>>` would read as a chain and a quote as exact-match toggle. Budget capping (:1662–1668): sweep capped by constant AND by caller's tighter deadline — "a tight `timeout_ms` is not overrun by the frames the caller never asked about."

**Flow:** read tools join `[main text, *frame texts]` under min(action-budget, 2s) → wait_for requires exactly-one-of selector/text → build per-frame wait tasks → gone ⇒ gather-all; appear ⇒ FIRST_COMPLETED loop draining all exceptions.
**Invariant:** every path through the dialog/frame handlers answers or drains (no orphan awaits); the vendor-assumption docstring bumps its date when facts are re-verified against the installed Playwright — porters must keep code+date together.

## Probe (direct test)
`tests/playwright/test_playwright.py::TestWaitFor` (gone-wait satisfied only when ALL frames released; appear-race returns on first match), iframe sweep tests (text from child frame included in `get_text` full-page), module-docstring facts cross-checked live in `scripts/playwright_smoke.py` (iframe scenario, dialog scenario, tab scenario).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_wait_in_any_frame _frame_text'
```

## Verdict
**Adopt** race-vs-gather wait duality + capped frame sweeps for any multi-frame automation. **Adopt** the dated external-assumption docstring discipline. **Omit** pixel-coordinate clicking if you don't expose it.
