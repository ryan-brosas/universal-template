<!-- capsule-v2 -->
# Mechanism honesty bounds — how does a capture note state what its target does NOT deliver?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** Where and how must a capture note bound its mechanism's power, so a porter inherits the limits along with the technique?

## The `Correct = X, not Y` acceptance clause
**Path/Symbol:** §5 Behavior contract of the four banner-generation notes: `browser-harness-get_ws_url.md:29`, `browser-use-BrowserSession.connect.md:28`, `growchief-cdpDetectionPass.md:26`, `jobspy-scrape.md:22` (the six-section skeleton's "Correct = ..." rule); plus the standalone honesty sentence in growchief §5 tail: "Not sufficient as our whole stealth layer."
**Signature:** `Correct = <the real outcome that counts>` + `, not <the plausible wrong one>`; the wrong side is always an adjacent over-claim (a launched Playwright Chromium vs attached user Chrome; a firmographics substitute vs joinable strings; a full stealth suite vs one narrow pass); edges are declared in the same contract line via an `Edges:` field.
**Data Shape:** four `Correct =` clauses, each pairing exactly one right/wrong contrast; three of them also carry explicit negative-delivery statements inside the same section (growchief "does not verify the leak is gone" + "Not sufficient as our whole stealth layer"; jobspy "will 429/block" constraint + "not contacts" output bound); the two Aug-18 notes (cuga, pah) carry the same honesty as bullet `Edge:` items instead — the bound moves form, never disappears.

### Decisive source
```markdown
Edges: none declared; it does not verify the leak is gone. Correct = subsequent
page JS sees a frozen Error prototype. Not sufficient as our whole stealth layer.
```
(`notes/growchief-cdpDetectionPass.md:26`)

and the attach-vs-launch contrast:
```markdown
Correct = a websocket Chrome will accept for Target/Page/Runtime, not a launched
Playwright Chromium.
```
(`notes/browser-harness-get_ws_url.md:29`)

**Flow:** define success observably ("subsequent page JS sees a frozen Error prototype") → immediately name the plausible over-claim a reader would otherwise make → declare undeclared/unverifiable edges explicitly ("none declared; it does not verify...") rather than omitting them → let downstream consumers cite the bound verbatim when they scope their own designs.
**Invariant:** every note bounds its target somewhere in §5 — through `Correct = X, not Y`, an `Edges:` field naming failure modes, or a bullet `Edge:` item; a note whose contract reads as unconditional praise fails this capsule. The bound is part of the CONTRACT, not a disclaimer footnote: it changes what a porter must build on top (growchief's pass alone is not stealth; JobSpy output joins onto Crunchbase, it does not replace it).
**Probe:** deterministic probes (notes dir): `grep -c 'Correct =' notes/growchief-cdpDetectionPass.md` = **1**, same for browser-harness / browser-use / jobspy = **1** each, cuga / pydantic-ai-harness = **0** (bullet-form contracts instead — expected by construction); `grep -cF ', not ' notes/browser-harness-get_ws_url.md` = **2**, jobspy = **4**; `grep -cF 'Not sufficient as our whole stealth layer' notes/growchief-cdpDetectionPass.md` = **1**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Not sufficient", limit: 5 });
// EXECUTED 2026-08-24 inspo-notes pass 10 (composition twin pattern:"not a lead CSV"): results: 1 —
// Section node inspo-notes.growchief-cdpDetectionPass.2.-The-flow-it-lives-in @ lines 8-9, proving
// the graph resolves honesty sentences to their owning note sections line-exact;
// search_graph BM25 total: 0 on this doc-shaped graph (standing caveat).
```

## Verdict
Adopt the Correct-not clause plus declared-edge grammar for every capability capture; adapt the wrong-side contrasts to your domain's characteristic over-claims; omit nothing from the bound when porting — dropping the "not Y" half converts a proven narrow tool into an imagined general one, which is precisely the failure this format exists to prevent.
