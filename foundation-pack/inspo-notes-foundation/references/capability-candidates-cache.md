<!-- capsule-v2 -->
# Capability→candidates discovery cache — what verdict vocabulary stops a team from re-evaluating the same OSS candidates?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** How is a discovery cache structured so every evaluated candidate carries a durable decision with its reason, instead of being re-researched next cycle?

## Capability blocks with closed verdicts
**Path/Symbol:** `candidates.md` — title line 1 (`# INSPO discovery cache — <capability, product use case>`), three `## Capability:` blocks (lines 3/8/13), candidate bullets with `verdict:` fields throughout.
**Signature:** per block: `## Capability: <capability + product use case>` then bullets `- <owner>/<repo> | use case: <why relevant> | verdict: <clone|maybe|skip> (<reason>) | link: <url>`.
**Data Shape:** verdicts are a closed vocabulary with mandatory reasons: `clone` = build on it now; `maybe` = keep, often with a condition ("already local — ingest from graph, do not re-clone", "only if we keep a Playwright adapter"); `skip` = rejected with the reason stated ("direct-scraper trap", "30k stars / 6 months — verify before any clone").

### Decisive source
```markdown
- stoicaandrei/crunchbase-scraper | use case: Crunchbase HTML scrape without API
  | verdict: skip (direct-scraper trap; not the CDP process) | link: ...
- CloakHQ/CloakBrowser | ... | verdict: skip (30k stars / 6 months — verify
  before any clone) | link: ...
- browser-use/browser-use | ... | verdict: maybe (already local; ingest from
  graph, do not re-clone) | link: ...
```
(`notes/candidates.md`, capability block 3)

**Flow:** state the capability and product use case as the heading → list every candidate repo with why-it-matters → stamp one of exactly three verdicts WITH its reason → later sessions read the cache and act on prior decisions instead of restarting discovery.
**Invariant:** every bullet carries a verdict and every verdict carries a reason (18 `verdict:` occurrences over 3 capabilities in the live file); "already cloned/indexed" candidates are marked so nobody re-clones; suspicious metrics are captured inside the skip reason rather than silently dropped. Probe anchors verified live: `grep -c '^## Capability:'` = 3; `grep -c 'verdict:'` = 18.
**Probe:** deterministic probe: after authoring or editing the cache, `grep -c 'verdict:' notes/candidates.md` must equal the candidate-bullet count and `grep -c '^## Capability:' notes/candidates.md` must match planned capabilities.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "Capability:", limit: 10 });
// resolves inspo-notes.candidates.Capability:-* Section nodes @ candidates.md (planned-capability headers)
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 3 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the three-verdict cache format for any build-vs-borrow evaluation; adapt the reason conventions to your risk rules; omit any scoring/ranking machinery — the cache deliberately stores human-readable reasons, not numbers.
