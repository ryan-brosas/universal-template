<!-- capsule-v2 -->
# License borrowing boundary — how does an inspect-only AGPL restriction get stamped so borrowed designs never become copied files?

**Source:** user-authored ingest notes over third-party repos (internal working notes; no upstream VCS), `/mnt/hdd/utopia/inspo/reference/notes`; Codebase Memory `inspo-notes`. **Question:** How must a capture note encode license boundaries so that learning from an AGPL repo never degrades into copying its code?

## Stamped-at-every-site restriction
**Path/Symbol:** `growchief-cdpDetectionPass.md` — banner stamp line 4 (`**Inspect only — do not copy.**`), constraint statement in section 4, and the note-level "not sufficient as our whole stealth layer" honesty line in section 5.
**Signature:** banner: `Provenance: <path>, <license>, ... **<restriction sentence>.**`; constraints entry: `<license> product, not a library → borrow WHY (<specific techniques>), never files.`
**Data Shape:** three reinforcement sites: (1) provenance banner directly under the license token, (2) a constraints bullet that converts the legal limit into an engineering instruction naming exactly WHAT may be borrowed (the why: logged-in profile, patchright not stock Playwright, detect pass before act), (3) capability-boundary honesty — the captured mechanism is explicitly scoped ("a narrow anti-detect, not a fingerprint suite").

### Decisive source
```markdown
- AGPL product, not a library → borrow WHY (logged-in profile, patchright not
  stock Playwright, detect pass before act), never files.
```
(`notes/growchief-cdpDetectionPass.md:21-22`, section 4)

with the banner one screen above:
```markdown
Provenance: `/mnt/hdd/utopia/inspo/growchief`, AGPL-3.0, indexed `growchief`
(2558 nodes / 7075 edges). `shared/server/bots/cdp.detection.pass.ts:3-33`.
**Inspect only — do not copy.**
```
(lines 3-4)

**Flow:** record license in the provenance header → immediately follow it with the restriction sentence → in Constraints, translate the license into a borrowing rule that names the portable ideas → scope the mechanism's real power honestly so nobody over-relies on it downstream.
**Invariant:** the restriction appears at BOTH banner and prose sites (verified live: `grep -c 'do not copy'` = 1 at banner; `grep -c 'borrow WHY'` = 1 in constraints); MIT sources get no such stamp (contrast `browser-harness-get_ws_url.md:3` = plain MIT) — the boundary is per-license, not decorative.
**Probe:** deterministic probe: `grep -c 'do not copy' notes/growchief-cdpDetectionPass.md` = 1 AND `grep -c 'AGPL' notes/growchief-cdpDetectionPass.md` ≥ 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "inspo-notes", pattern: "AGPL", limit: 10 });
// resolves inspo-notes.growchief-cdpDetectionPass Module @ growchief-cdpDetectionPass.md:3 (license banner) + candidates.md rows
// (EXECUTED 2026-08-24 docs-knowledge pass 9: 3 result; search_graph query/name_pattern forms return 0
//  on this doc-shaped graph — Section nodes are tokenless/filtered; search_code is the working primitive)
```

## Verdict
Adopt the two-site stamping pattern (banner + constraints rule) for every restricted-license capture; adapt the restriction wording to the specific license family; omit any code transcription from restricted repos even when the note pins exact line ranges — the pins exist to enable graph retrieval and design study, not vendoring.
