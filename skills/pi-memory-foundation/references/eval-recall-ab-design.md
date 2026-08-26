<!-- capsule-v2 -->
# Eval recall A/B design — how do you prove selective injection actually helps recall, not just that memory exists?

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z). **Question:** How do you measure whether context injection improves agent recall — isolating the injection effect from baseline knowledge and from tool use?

## Eval recall A/B design
**Path/Symbol:** `test/eval-recall.ts` — `QUESTIONS` (:216–326), `CORPUS` (:62–204), `runEvalRound` (:453–487), `printResults` (:489–581), `main` (:583–669).
**Signature:** `runEvalRound(): QuestionResult[]` — per question runs Mode A `runPi(prompt)` vs Mode B `runPi(prompt, { PI_MEMORY_NO_SEARCH: "1" })`, scoring each with `scoreResponse(textOutput, expectedKeywords)` (`expectedKeywords.some(kw => lower.includes(kw))`).
**Data Shape:** 25 seeded entries (`target: "long_term"` → MEMORY.md stamped `<!-- entry-N -->`; `target: "daily"` → `daily/YYYY-MM-DD.md` at ages today/−1/−3…−30) × 15 questions keyed `{ id, question, expectedKeywords[], source: long_term|today|yesterday|older_daily, topic }`.

### Decisive source
```ts
// :456-479 — both arms get the SAME no-tools prompt; only the env differs
const prompt =
  "Based on the context you have available, answer this question concisely. " +
  "Do NOT use any tools — only use what's already in your context. " +
  `If you don't know, say "I don't know."\n\nQuestion: ${q.question}`;

// Mode A: with selective injection
const withSearch = runPi(prompt);
...
// Mode B: without selective injection
const withoutSearch = runPi(prompt, { PI_MEMORY_NO_SEARCH: "1" });
...
const indicator = hitA && !hitB ? "+" : hitA === hitB ? "=" : "-";
```

**Flow:** preflight pi (`say OK` round-trip) and qmd (`qmd status`) → backup real memory files (suffix `.eval-backup`) → seed corpus → `qmd update` → per question run A then B → aggregate majority across `EVAL_RUNS`, print per-question deltas and by-source rates → `finally` restore every backed-up file.
**Invariant:** the A/B delta is only attributable to injection because BOTH arms share the identical anti-tool prompt (the model can never compensate via `memory_search`) and the same fresh corpus; a hit in BOTH arms (=) measures baseline leakage, not injection. The kill switch must actually disable search (see `before_agent_start` per-turn branch) or arm B is fake.
**Probe:** EXECUTED this pass (deterministic soundness check): extracted CORPUS/QUESTIONS from source and verified every question's `expectedKeywords` appear in ≥1 corpus entry of its declared source class → `corpus=25 questions=15 unsound=0 SOUND` exit 0. Live A/B execution additionally requires `pi` on PATH + API key + `qmd` collection (runner-blocked here: qmd absent; record as coverage caveat).
**Coverage caveat:** live LLM arms were not executed in this environment (no qmd binary); the soundness probe pins the harness's internal validity, not end-to-end recall rates.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "seedCorpus runEvalRound eval-recall QUESTIONS", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-arm same-prompt design (env-only differential) plus keyword-hit scoring with per-source breakdowns for ANY retrieval-injection feature. Adapt the corpus/questions to your domain; keep ages spread so date-window effects are visible. Omit nothing structural — but do not cite its numbers as upstream benchmarks.
---
