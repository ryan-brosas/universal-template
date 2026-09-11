<!-- capsule-v2 -->
# Two-tab domain isolation for cross-site workflows — how do you post to site B using data read from site A without triggering leave-site popups?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When one automation pass must navigate two different domains, why does each domain get its own dedicated tab, and how are tab indices pinned when refs shift every snapshot?

## Current-tab-is-HF, created-tab-is-X pinning with ANSI-stripped active-tab discovery
**Path/Symbol:** `workflows/executors/hf-papers-to-x.ts`:`getActiveTabIndex` (`:198-204`), `tabHF`/`tabX` state (`:206-207`), `switchToHF`/`switchToX` (`:209-218`), X-tab creation + teardown (`:503-509`, `:546-551`).
**Signature:** `getActiveTabIndex(): number`; `switchToHF(): void`; `switchToX(): void` (no-op until `tabX >= 0`).
**Data Shape:** `tabHF = getActiveTabIndex()` at module load (the tab the workflow started in); `tabX = -1` sentinel until `ab('tab new')` + re-read. Tab commands travel through the shared `ab()` CLI wrapper (30 s timeout, stderr narration on failure, `''` return).

### Decisive source
```ts
function getActiveTabIndex(): number {
  const listing = ab('tab list')
  // Strip ANSI escape codes, then find active tab marked with → prefix
  const clean = listing.replace(/\x1b\[\d*m/g, '')
  const match = clean.match(/→\s*\[(\d+)\]/)
  return match ? parseInt(match[1]!, 10) : 0
}
let tabHF = getActiveTabIndex()  // Current tab becomes HF tab
let tabX = -1                    // Will be set when Tab 2 is created
...
// This avoids cross-domain navigation which triggers Chrome "Leave site?" popups.
```

**Flow:** pin `tabHF` = whatever tab is active at start → do ALL HuggingFace work there (paper list + per-paper abstract pages: same-domain navigation) → before posting, `tab new`, re-read the active index into `tabX`, open x.com/home once → per paper: `switchToX()` (open /home, upload, fill, Post, self-reply — all same-domain) → after the loop: switch to X tab, `tab close`, switch back to HF. Every switch is followed by a small `wait 300` so the CLI's target settles.
**Invariant:** One domain per tab, forever. Cross-domain navigation inside a logged-in tab is what raises Chrome's "Leave site?" beforeunload dialog — an unrecoverable modal for a headless-ish pipeline. Tab indices are captured ONCE and reused; you must never assume index 0/1 because the browser may have pre-existing tabs. The active-tab marker is matched AFTER stripping ANSI color codes (the raw listing wraps `→ [N]` in escapes). `switchToX()` before creation must be a safe no-op (`tabX < 0` guard), not an error.
**Probe:** No upstream executor tests exist (browser pipelines; repo tests cover only `scripts/lib/*` + log-operation). Deterministic source-grounded probes: isolation comment at `hf-papers-to-x.ts:192-195`, ANSI strip at `:200-203`, teardown ordering at `:546-550`. Coverage caveat recorded; port with your own smoke test against a real CDP browser.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getActiveTabIndex switchToHF switchToX tab", limit: 10 });
```
Graph resolves `getActiveTabIndex` :198-204 (inbound caller: hf-papers-to-x only), plus sibling `abEval` copies across all five executors.

## Verdict
Adopt per-domain tab pinning with captured-once indices, ANSI-stripped active-tab discovery, no-op-until-created switches, and explicit close-and-return teardown. Adapt the CLI verbs to your browser driver. Omit single-tab navigation flows entirely — if your two sites can't share a tab without modals, this pattern is the fix; if they can, extra tabs are unneeded complexity.
