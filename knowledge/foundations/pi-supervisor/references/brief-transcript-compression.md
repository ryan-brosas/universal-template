<!-- capsule-v2 -->
# Brief-transcript compression — how does a full conversation become a bracketed transcript that fits the prompt?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What are the truncation budgets, the collapse rules for repeated calls/errors, and why is the tool-call cap TAIL-KEEPING?

## buildBriefSections + stringifyBrief (`src/compaction/brief.ts`)
**Path/Symbol:** `src/compaction/brief.ts:buildBriefSections` (:231-388), `stringifyBrief` (:393-414), `truncateTokens` (:131-149), `compressBash` (:158-177), `capBrief` in format.ts (:41-51).
**Signature:** `(blocks) => BriefLine[]`; budgets: user 256 content-words, assistant 200, HCA turn summaries 12; `TOOL_CALLS_PER_TURN=8`, `BASH_CAP=120`.
**Data Shape:** Sections `[user]`, `[assistant]`, `[tool_error] <tool> (#N)` with per-line `(#sourceIndex)` refs.

### Decisive source
```ts
// Word-aware truncation: STOPWORDS don't count toward budget (replaces Intl.Segmenter, ~2× slower)
while ((match = CONTENT_WORD_RE.exec(flat)) !== null) {
  if (!STOP_WORDS.has(match[0].toLowerCase())) { count++; if (count > limit) { cutIdx = match.index; break; } }
  cutIdx = match.index + match[0].length;
}
// bash semantic compression: first line, strip `cd X && `, strip pipe tails (head|tail|sort|wc...) up to 3×, cap 120
// Collapse identical consecutive tool lines into one with ref list + count:
out[out.length-1] = `${base} (${m[2]}, #${ref}) x${parseInt(m[3]) + 1}`;
// Cap tool calls per [assistant] turn — KEEP TAIL:
const dropCount = toolIdxs.length - TOOL_CALLS_PER_TURN;
next.push(`* (${dropCount} earlier tool-call entries omitted)`);   // explicit omission marker
// Collapse consecutive identical [tool_error] sections (same tool AND same body):
prev.header = `[tool_error] ${tool} (${refs}) x${count}`;
```

**Flow:** blocks → per-kind lines (user/bash under `[user]` with `$ cmd`, assistant text + tool one-liners under `[assistant]`, errors as own sections) → self-talk prefix strip ("hmm/wait/actually…" up to 2×) → identical-tool-line collapse (`(#1, #3) x2`) → per-turn tail-keeping cap of 8 tool lines with an explicit "(N earlier ... omitted)" placeholder → identical-error-section collapse → stringify with blank-line suppression between consecutive all-tool sections → final `capBrief` keeps LAST 120 lines but re-cuts to the first section header so no section opens mid-air.
**Invariant:** (1) Truncation counts CONTENT words only — stopword-heavy text survives nearly verbatim. (2) Tail-keeping is deliberate: "latest actions tend to be the deciding edits/writes; head is usually exploration noise" (in-code comment). (3) Every lossy cut leaves a marker (`...(truncated)`, `(N earlier tool-call entries omitted)`, `...(... earlier lines omitted)`) so the judge can distinguish silence from elision. (4) Error-collapse requires BOTH tool and body equality.
**Probe:** `tests/full-fidelity-snapshot.test.ts` `produces a brief transcript` (:199-216); constants pinned at brief.ts :7-8/:153/:332 and format.ts :9.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "buildBriefSections truncateTokens compressBash TOOL_CALLS_PER_TURN", limit: 8 });
```

## Verdict
Adopt bracketed-section transcripts, stopword-budgeted truncation, tail-keeping caps, and always-marked elision. Adapt budgets to your model's context. Omit skill-tag collapse if your host has no `<skill>` injections.
