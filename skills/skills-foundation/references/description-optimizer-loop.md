<!-- capsule-v2 -->
# Description Optimizer Loop — how does an LLM rewrite a skill description from eval failures without overfitting to them?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the exact contract of the eval-driven description-improvement call — transport, prompt structure, anti-overfitting rules, and the length-limit safety net?

## claude -p as a stateless optimizer with history-aware anti-repetition
**Path/Symbol:** `skills/skill-creator/scripts/improve_description.py::improve_description` (:50–191) + `_call_claude` (:20–47); orchestrator `run_loop.py`.
**Signature:** `improve_description(skill_name, skill_content, current_description, eval_results, history, model, ...) -> str`; `_call_claude(prompt: str, model: str | None, timeout=300) -> str`.
**Data Shape:** failures split into `failed_triggers` (should_trigger ∧ ¬pass) and `false_triggers` (¬should_trigger ∧ ¬pass), each rendered with per-query trigger counts (`triggered N/M times`). History entries carry their score string in the XML tag itself: `<attempt train=3/5, test=1/2>` + full prior description. Output parsed from `<new_description>...</new_description>` (DOTALL regex; falls back to whole text stripped of quotes).

### Decisive source
```python
# Remove CLAUDECODE env var to allow nesting claude -p inside a
# Claude Code session. The guard is for interactive terminal conflicts;
# programmatic subprocess usage is safe.
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
```
```
PREVIOUS ATTEMPTS (do NOT repeat these — try something structurally different):
<attempt train=2/5>
Description: "..."
</attempt>
...
Concretely, your description should not be more than about 100-200 words,
even if that comes at the cost of accuracy. There is a hard limit of 1024
characters — descriptions over that will be truncated, so stay comfortably under it.
...generalize from the failures to broader categories of user intent...
```
```python
# Safety net: ... if the model blew past it anyway, make one fresh single-turn
# call that quotes the too-long version and asks for a shorter rewrite.
if len(description) > 1024:
    shorten_prompt = f"{prompt}\n\n---\n\nA previous attempt produced this
    description, which at {len(description)} characters is over the 1024-character
    hard limit: ... Rewrite it to be under 1024 characters ..."
```

**Flow:** split results by polarity → build scores summary (Train / optional held-out Test) → embed current description + both failure lists WITH counts + full attempt history → prompt rules: imperative phrasing ("Use this skill for"), user-intent over implementation, distinctiveness vs competing skills, GENERALIZE-don't-enumerate (two named reasons: avoid overfitting + descriptions inject into ALL queries so space is scarce), 100–200 word target under the 1024 hard cap → `claude -p --output-format text` on STDIN (prompt embeds the full SKILL.md body and would exceed argv limits) → parse tags → if >1024 chars: one fresh single-turn rewrite call inlining the too-long output (claude -p is one-shot; the old SDK multi-turn correction became prompt-inlining).
**Invariant:** The optimizer optimizes TRIGGERING ONLY — it never sees body content quality. Anti-overfit is structural: failure lists always come with generalization instructions AND every prior attempt is shown with its scores tagged "do NOT repeat", so the LLM walks a diverse search rather than hill-climbing on one phrasing family. run_loop grabs the highest-scoring attempt at the end — the loop is best-of-N with creative mixing explicitly encouraged, not gradient descent.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'CLAUDECODE' skills/skill-creator/scripts/improve_description.py` = 2; `grep -c 'over the 1024-character hard limit' skills/skill-creator/scripts/improve_description.py` = 1. Behavioral: the transcript dict records prompt/response/char_count/over_limit per iteration to `improve_iter_N.json` — replayable audit trail.
**Coverage caveat:** no direct upstream test suite; contract pinned to source lines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "improve_description", limit: 5 });
// skills.skills.skill-creator.scripts.improve_description.improve_description Function improve_description.py 50-191
```

## Verdict
Adopt the shape for any LLM-in-the-loop parameter optimization: stdin transport, tag-delimited output parsing, polarity-split failure evidence with counts, history-as-negative-examples, soft-target + hard-limit + single-turn-rewrite safety net, JSONL transcript per iteration. Adapt the subprocess target (any CLI LLM). Omit the Claude-specific auth commentary outside Claude Code hosts.
