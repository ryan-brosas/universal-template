<!-- capsule-v2 -->
# Trigger Description Authoring — how is a skill description written and optimized so the model actually triggers it?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96`; Codebase Memory `skills`. **Question:** What makes a description trigger reliably, and what is the optimization loop that improves trigger accuracy without overfitting?

## Description authoring + eval-driven description optimization
**Path/Symbol:** `skills/skill-creator/SKILL.md` — "Write the SKILL.md" (description guidance, line 67) and "Description Optimization" (graph Section `skills.skills.skill-creator.SKILL.Description-Optimization`, lines 333-334; loop in `scripts/run_loop.py`).
**Signature:** `python -m scripts.run_loop --eval-set <trigger-eval.json> --skill-path <skill> --model <model-id> --max-iterations 5`.
**Data Shape:** Eval set = JSON array of `{query, should_trigger}` (20 items: 8-10 should-trigger covering phrasing variants, 8-10 near-miss negatives). Output: `best_description` selected by held-out TEST score, not train score.

### Decisive source
```markdown
**description**: When to trigger, what it does. This is the primary triggering
mechanism - include both what the skill does AND specific contexts for when to
use it. All "when to use" info goes here, not in the body. Note: currently
Claude has a tendency to "undertrigger" skills ... To combat this, please make
the skill descriptions a little bit "pushy".
...
It splits the eval set into 60% train and 40% held-out test, evaluates the
current description (running each query 3 times to get a reliable trigger
rate), then calls Claude to propose improvements based on what failed.
```

**Flow:** Write pushy description listing concrete trigger phrases → generate 20 realistic queries mixing should-trigger with genuinely tricky near-misses ("don't make should-not-trigger queries obviously irrelevant") → user reviews/edits the set via HTML template → optimization loop: split 60/40 train/test, run each query ×3 for trigger rate, propose improved description from failures, iterate ≤5 → pick best by test score → write back into frontmatter.
**Invariant:** The description alone determines triggering (the body is not consulted at decision time); selection must use held-out test score to avoid overfitting the wording to the eval set. Also: queries must be substantive multi-step tasks — simple one-step queries may not trigger regardless of description quality.
**Probe:** `skills/skill-creator/scripts/run_eval.py` / `run_loop.py` execute the loop; the doc pins observable behavior: "returns JSON with `best_description` — selected by test score rather than train score to avoid overfitting."

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "Description Optimization triggering eval", limit: 10 });
```

## Verdict
Adopt: pushy descriptions with explicit trigger contexts, near-miss negative queries, train/test split with test-score selection, 3× repetition for rate estimation — all host-independent. Adapt the runner (`claude -p` subprocess) to your own model gateway; the real-product examples (dashboards) are Anthropic-flavored. Omit the HTML review-template mechanics unless you also want human-in-the-loop eval curation. Caveat: depends on an external CLI at runtime; no unit tests ship for the loop scripts.
