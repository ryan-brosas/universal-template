<!-- capsule-v2 -->
# Entry-format social contract — the design.md knowledge-entry vocabulary that NO code enforces

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839` `docs/design.md`; Codebase Memory `pi-memory-extension`. **Question:** Which parts of this repo's memory contract are CODE vs CONVENTION — a porter who implements only what TypeScript enforces ships a store that cannot answer "is this decision still active?", because lifecycle fields live only in docs and human discipline.

## Documented entry format (`docs/design.md:170-196`)
**Path/Symbol:** `docs/design.md` "Entry Format" section (:170-196); field table :192-196; philosophy statement 1 at :39; session-history boundary at :43. Zero references in `pi-memory.ts`.
**Signature:** none — no parser, no schema, no validation anywhere in source (`grep -n 'supersedes\|confidence\|valid_from' pi-memory.ts` ⇒ zero matches).
**Data Shape:** every entry is an `## <date> <title>` heading plus a bullet list of optional fields: `status` (active / superseded / deprecated), `valid_from`, `supersedes`, `context`, `decision`, `rationale`, `consequences`, `confidence` (high/medium/low), `verified`.

### Decisive source
```markdown
## 2026-07-15 Choosing Chroma as Vector Store

- **status**: active                  ← active / superseded / deprecated
- **valid_from**: 2026-01             ← optional, when this decision applies
- **supersedes**: —                   ← optional, older entry replaced by this one
...
- **confidence**: high               ← high / medium / low
- **verified**: 6 months production without issues
```
(from `docs/design.md:172-190`; field table pins which fields apply to which entry kinds)

**Flow (the actual enforcement chain):** human writes entries in this shape → nothing validates them → files are injected verbatim into the prompt (subject to per-file truncation) → the MODEL reads status/supersedes/confidence as prompt context and reasons with them → humans update them during review/promote.
**Probe:** NO upstream tests exist; this seam lives OUTSIDE code by design, so the probe is mechanical-negative. Pass-3 audit re-executed: `grep -c 'supersedes\|confidence\|valid_from' pi-memory.ts` = **0** (rc 1) at pin f3b4377f — zero parser/validation surface confirmed; `sed -n '170,196p' docs/design.md` renders the field table verbatim as cited above.
**Invariant:** The entry format is a SOCIAL CONTRACT between humans and the model, not a data format between code and disk: the loader treats files as opaque text, so a malformed or missing `status` degrades silently into weaker model reasoning rather than an error. The three principles behind it are also unenforced-by-code but load-bearing for porters: (1) "Human decides what becomes memory" (:39) — auto-generated checkpoints are candidates that are never shown to the model until promoted; (2) "Markdown is the source of truth" — diffable/revertible, no vector DB; (3) "Session history is not memory" (:43) — Pi's JSONL keeps raw logs, `memory/` holds distilled knowledge. A porter must decide consciously whether to keep convention-only (zero parser = zero drift surface) or promote fields to validated frontmatter — either is defensible; accidentally half-implementing (parsing some fields, ignoring others) is not.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", query: "entry format status confidence", limit: 10, semantic_query: ["memory entry metadata fields"] });
```
(Graph indexes `docs/design.md` as prose nodes — coverage check returns `no_recorded_issue`/`metadata_match`; the contract itself lives outside code, confirmed by whole-file read of `pi-memory.ts`.)

## Verdict
Adopt the field VOCABULARY (status/supersedes/confidence/verified) as the minimum viable memory-entry schema for any human-curated store — it is what makes entries lifecycle-manageable by both humans and models. Adapt storage shape freely (frontmatter, table, bullets). Omit any parser if you keep the human-curation loop; add validation ONLY as a deliberate upgrade, never half-way. Coverage caveat: docs-plane seam — verified by direct read of design.md:170-196 + negative grep over pi-memory.ts.
