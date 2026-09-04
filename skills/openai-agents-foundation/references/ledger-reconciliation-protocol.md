<!-- capsule-v2 -->
# Ledger reconciliation — how does a durable learning ledger recover from a missed pass write without touching sibling rows?

**Source:** OpenAI Agents Python MIT `main@fe45b415` (process seam; evidence is this leaf's own work records + on-disk state). **Question:** When pass N delivered its artifacts but the shared ledger row still reads pass N−1, how do you reconcile counts and history in one scoped edit without a stale whole-file replacement?

## Detect, verify on disk, then one scoped row edit
**Path/Symbol:** work records `$REFERENCE_ROOT/.skill-mining-work/openai-agents-python/{state,research,verification}.md`; ledger `$REFERENCE_ROOT/.skill-mining-work/llm-repo-learning.md` row `openai-agents-python`.
**Signature:** reconciliation precondition: `pass-8 verification.md` records completion + parity (75 refs / 75 v2 / 75 loader) AND the ledger row still reads `pass 7 | 71 | 71`.
**Data Shape:** row columns `Source | Foundation | Graph project | Pin | Pass | Refs | V2 | Last pass | Next-pass targets | Blockers`; the Status board line mirrors pass/refs/v2.

### Decisive source
```text
# state.md (pass 8 completion):
refs: 75 reference files after pass (71 before) | capsule-v2: 71 → 75 (+4 this pass)
# ledger row before reconciliation (line 285):
| openai-agents-python | ... | 7 | 71 | 71 | 2026-08-27 pass7 ... |
# ⇒ pass-8's ledger write never landed; reconcile to pass 9 in ONE own-row edit,
# never by rewriting the whole file (sibling rows must stay byte-for-byte).
```

**Flow:** detect the divergence by reading the ledger fresh (never from memory) → verify the leaf's on-disk truth before trusting either side: count `references/*.md`, count the capsule-v2 markers, count loader lines in SKILL.md — if these disagree, repair the LEAF first and only then touch the ledger → compose the replacement row outside the shared file (pass 9, refs 79, v2 79, last-pass summary folding in the missed pass-8 delivery) → re-read the row immediately before writing, apply an exact own-row string replacement → read back the row and the Status board line after writing; one retry on anchor drift, then leave the ledger untouched and report.
**Invariant:** sibling rows are byte-for-byte untouched; the reconciled counts equal the verified on-disk parity (not the recorded intent); a second anchor drift aborts the write rather than forcing it.
**Probe:** post-write `grep -n "openai-agents-python" llm-repo-learning.md` shows exactly one main-table row at pass 9 / 79 / 79 plus the matching Status board line; `ls references | wc -l` == 79 and marker count == 79.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "pass 8 completion refs 75 capsule-v2 parity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt disk-truth verification before ledger reconciliation and the compose→re-read→scoped-edit→read-back protocol. Adapt the column layout to your ledger schema. Omit nothing — a stale whole-file rewrite that deletes sibling rows is the failure this capsule exists to prevent. Coverage caveat: process seam; evidence is work-record + on-disk parity, not repo source.
