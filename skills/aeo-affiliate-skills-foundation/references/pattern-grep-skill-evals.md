<!-- capsule-v2 -->
# Pattern-grep skill evals — how do you behavior-test prompt-skills with zero test framework?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** When the "unit" under test is a markdown instruction file interpreted by an LLM, what is the minimal harness that still yields CI-usable pass/fail evidence?

## Whole-skill prompt embedding + case-insensitive all-pattern grep judging
**Path/Symbol:** `scripts/run-evals.sh` (whole file; prompt build :139–147, run+judge :151–184, results log :186–197, exit :214); manifest `evals/evals.json` (`{version, description, skills:{slug:{tests:[{id,name,input_prompt,expected_patterns[],pass_criteria}]}}}`).
**Signature:** bash CLI `run-evals.sh [--dry-run] [--verbose] [--model NAME] [SKILL_SLUG]`; model invocation `timeout "${TIMEOUT}s" claude --model "$MODEL" --print --no-input "$PROMPT"`; env knobs `EVAL_MODEL` (default sonnet), `EVAL_TIMEOUT` (default 120 s).
**Data Shape:** Per-test artifact: full output saved to `evals/results/${TEST_ID}.txt`; run summary appended to timestamped `evals/results/run-YYYYmmdd-HHMMSS.json` as `{id, skill, name, status: pass|fail|error, missing}`. Totals: PASS/FAIL/SKIP/TOTAL counters; exit code non-zero iff any FAIL.

### Decisive source
```bash
PROMPT="You are an AI executing an affiliate marketing skill. Read the skill instructions below, then respond to the user prompt.

--- SKILL INSTRUCTIONS ---
$(cat "$SKILL_MD")
--- END SKILL ---

USER PROMPT: $INPUT

Execute the skill now. Produce the full output as specified in the skill's Output Format section."
...
if timeout "${TIMEOUT}s" claude --model "$MODEL" --print --no-input "$PROMPT" > "$OUTPUT_FILE" 2>/dev/null; then
  PASS=true
  for PATTERN in $PATTERNS; do
    if ! grep -qi "$PATTERN" "$OUTPUT_FILE" 2>/dev/null; then
      PASS=false
      MISSING="$MISSING $PATTERN"
    fi
  done
```

**Flow:** dependency gates (`jq`, `claude` CLI) fail fast → select skills via `jq -r '.skills | keys[]'` optionally filtered by slug → locate each skill dir by `find skills -name "$SKILL" -type d | head -1` (missing dir = warn-and-skip, not failure) → per test: embed the ENTIRE SKILL.md plus the user prompt in one message, run under timeout, require EVERY `expected_patterns[]` entry via case-insensitive grep of the saved output; missing patterns are reported by name; timeout/error counts as skip(status error); everything appended to the run log; final exit mirrors failures.
**Invariant:** The judge is deliberately shallow and deterministic — presence of expected substrings — so CI never flakes on LLM phrasing; depth lives in the human-readable `pass_criteria` field, which the runner does NOT enforce (it documents the bar for humans/reviewers). Pattern lists therefore must encode structural anchors of the Output Format section ("Top Pick:", "Score", "Next Steps"), not semantic quality.
**Probe:** Deterministic shape pins executed: `grep -n "expected_patterns" scripts/run-evals.sh` → :124 (extraction), :155 (grep loop); `grep -n "pass_criteria" scripts/run-evals.sh` → zero matches (proving prose criteria are unenforced). Live model runs were NOT executed this lane (needs `claude` auth); `--dry-run` path inspected as source. Recorded honestly in verification.md.
**Coverage caveat:** none — `scripts/run-evals.sh` checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "evals runner expected patterns claude print", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when you need behavioral smoke tests for prompt-defined skills in CI without any eval framework or API keys beyond the agent CLI itself: whole-instruction embedding, substring judging, timeout→skip, named-missing-pattern reporting, machine-readable run logs. Adapt the judge upward (LLM-as-judge) only out-of-band — keep the deterministic grep tier for CI. Omit reliance on `pass_criteria` for automation; treat it as spec documentation. Note the string-concatenated JSON log is injection-prone if prompts contain quotes — regenerate it with a real JSON writer in any serious port.
