<!-- capsule-v2 -->
# Checkpoint timestamp encoding — how does an ISO instant become a sortable, filesystem-safe filename?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must reproduce the exact checkpoint filename contract — which characters are replaced and in what order — or checkpoints stop sorting chronologically / become unwritable on colon-hostile filesystems.

## Timestamp → filename ladder (`/memory:checkpoint`)
**Path/Symbol:** `pi-memory.ts:500-503` (inside the checkpoint handler :481–530).
**Signature:** local derivation: `new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)` interpolated as `checkpoint-<ts>.md`.
**Data Shape:** `checkpoint-2026-08-24T09-30-00.md` — 19-char ISO prefix with every `:` and `.` swapped to `-`, plus the `.md` extension.

### Decisive source
```ts
const ts = now.toISOString().replace(/[:.]/g, "-").slice(0, 19);
const fileName = `checkpoint-${ts}.md`;
const inboxPath = path.join(inboxDir, fileName);
```

**Flow:** capture `Date.now` as ISO-8601 UTC string (`YYYY-MM-DDTHH:MM:SS.sssZ`) → replace BOTH `:` and `.` with `-` FIRST → slice to 19 chars (drops milliseconds + `Z`) → interpolate into the fixed `checkpoint-.md` shell.
**Invariant:** Order matters: replace-then-slice means the 19-char window contains no millisecond fragment to half-replace; slicing first would strand a trailing partial `.sss` that renders inconsistently. Both separators are replaced because both are hostile — `:` breaks Windows filenames/colon-parsing tools, `.` would make the stamp collide with extension-detection heuristics. The result is lexicographically ordered == chronologically ordered (fixed-width fields), so inbox listing by name is a chronological review queue feeding `/memory:promote`. Filename granularity is whole SECONDS — two checkpoints within one second overwrite silently (`fs.writeFile`, not append); acceptable because checkpoints are human-paced. Note the deliberate asymmetry vs the promote separator's `_Promoted from [inbox/<file>]_` provenance line: the source filename IS the provenance record, so its encoding must round-trip through human review unchanged.
**Probe:** executed Node probe P4a-c (GREEN): encoding exact for a known instant, no `:`/`.` in the timestamp part, filename starts with `checkpoint-<ISO date>` so date-sorted directory listings stay chronological.

## Get live surrounding code
**Retrieve:** graph BM25 has NO Function node for the checkpoint closure (`search_graph "checkpoint"` = total:0 — anonymous handlers don't tokenize), so resolve by content search instead:
```bash
codebase-memory-mcp cli search_code '{"project":"pi-memory-extension","pattern":"checkpoint-"}'
```
(Executed pass-3 audit at pin f3b4377f: rank-1 `pi-memory` Module lines **502;536** — the filename ladder :502 and promote's inboxFile example :536; docs/design.md Module carries 5 doc hits. Drift note added [DONE:447 erratum class]: original `search_graph` block was dead-but-harmless metadata.)

## Verdict
Adopt replace-then-slice ISO stamping for any timestamped candidate/artifact filename (sortable + portable). Adapt the prefix and extension to host conventions; keep second-level granularity only when writes are human-paced. Coverage caveat: no upstream suite — pinned by executed probe at HEAD.
