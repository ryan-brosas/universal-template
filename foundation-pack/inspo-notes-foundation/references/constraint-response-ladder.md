<!-- capsule-v2 -->
# Constraint→response rationale ladder — how does §4 record WHY a mechanism looks the way it does, not just what it is?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** What grammar makes the Constraints section a transferable design rationale instead of a feature list, so a porter reproduces the *response* and not just the mechanism?

## The `constraint → response` ladder
**Path/Symbol:** section 4 of every INGEST note (`browser-harness-get_ws_url.md:21`, `browser-use-BrowserSession.connect.md:19`, `cuga-agent-PolicySystem.md:17`, `growchief-cdpDetectionPass.md:18`, `jobspy-scrape.md:16`, `pydantic-ai-harness-BrowserUse.md:16`); graph Section nodes `.4.-Constraints-that-shaped-it` at those anchors.
**Signature:** each bullet: `<observed constraint or failure mode>` + ` → ` + `<the concrete response the implementation makes>`; the arrow is Unicode `→` (U+2192), one per rung; constraint side names a real-world force (browser version lockdown, stale state on disk, cost ceilings, hostile page content), response side names the mechanism chosen BECAUSE of it.
**Data Shape:** 25 rungs across six notes (bh 5 · bu 4 · cuga 5 · gc 4 · js 1 · pah 6); several responses cross-reference their own §3 neighborhood symbol (`_devtools_port_live` answers "stale port files"; `trust_env=not is_localhost` answers "proxy env on localhost"), which is what welds rationale to structure.

### Decisive source
```markdown
- Chrome M136 default-profile lockdown → dedicated `--user-data-dir` + `BU_CDP_URL`
  avoids the dialog.
- Stale port files after Chrome quit → liveness check, do not trust UUID path,
  re-query `/json/version`.
```
(`notes/browser-harness-get_ws_url.md:23-24`)

and the version-pinned form:
```markdown
- Proxy env on localhost → `trust_env=not is_localhost`.
```
(`notes/browser-use-BrowserSession.connect.md:22`)

**Flow:** observe a force that shaped the design (often an incident class: a Chrome release breaking default profiles, a hung worker, a hijacked page) → write it verbatim as the left side → write the implementation's actual counter-move as the right side → keep one force per rung so the mapping stays decidable → a porter reading only this section can predict why each neighborhood symbol exists before opening its source.
**Invariant:** every note carries at least one arrow rung and every rung pairs a WHY with a HOW — a bullet that states a fact with no arrow ("Chrome 147+ returns 404") belongs in §1/§2, not here. The ladder is the anti-port-wrong device: porting `connect` without `trust_env=not is_localhost` re-derives the Windows 502 bug the rung records.
**Probe:** deterministic probes (notes dir): `awk '/^## 4\. Constraints/,/^## 5\./' notes/<note>.md | grep -c '→'` = **5** browser-harness, **4** browser-use, **5** cuga, **4** growchief, **1** jobspy, **6** pydantic-ai-harness (total 25); plus corpus-wide `grep -c '→' notes/candidates.md` = **2** (both inside capability headings' propose→approve→verify→audit phrasing — heading decoration, NOT constraint rungs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Constraints that shaped it", limit: 10 });
// EXECUTED 2026-08-24 inspo-notes pass 10: results: 6 — .4.-Constraints-that-shaped-it Section nodes,
// line-exact at 21/19/17/18/16/16. search_graph BM25 total: 0 on this doc-shaped graph;
// search_code is the working primitive (pass-9 caveat re-confirmed live).
```

## Verdict
Adopt the one-force-per-rung arrow grammar for any capture note whose target embodies a non-obvious trade-off; adapt the constraint taxonomy to your domain (version pinning, staleness, cost, trust boundaries are the observed families); omit rationale-free mechanism descriptions from §4 entirely — if you cannot name the force that shaped a choice, the honest entry is in §3 as a neighborhood pointer while the open question goes to the work record, not into invented rationale.
