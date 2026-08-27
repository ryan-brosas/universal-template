---
name: leverage-playbook
description: "Use when running the AI development loop — prep a session, prewalk a small/cheap model, decide code-vs-markdown, close out a session, or scale work faster: give agents context and let them search context, treat code as the ground truth (not specs), run the capture-into-skills ritual after every meaningful session, prefer verifiable outcome gates over humane, and stack carried code+skills so each new build is faster than the last. Verbatim Discord source: Tom, 7/26–8/21/26."
---

# Leverage Playbook — context-first, code-as-truth, skills capture

## Core Principle

Context, code, and captured skills carry the leverage — not hand-scripted plans. Every asset you keep makes the next build faster (2h → 20m → 30s).

## When to Use / NOT

- **Use when:** kicking off or re-entering a work session; using a small/cheap model (deepseek flash) for real delivery; deciding how much to spec in markdown vs just build; ending a meaningful session; or making a project's AGENTS.md/rules.
- **NOT when:** a single-shot prompt covers the change; a throwaway fix has no reusable seam; or a run is under ~1 session.

## Workflow

1. **Prep context, not plans.** Scope the task, show the agent where the relevant code/skills live, and let it *search* context itself. The prompt planning phase matters, but it feeds context — it does not hand script every step.
2. **Code is ground truth.** Prefer code + small examples to long markdown specs. A change that 1–2 examples could one-shot does not warrant a spec; markdown documents *post-code* state, and only burn a run-4–10-day plan into a durable artifact (see note about the chat session itself as an artifact).
3. **Let it probe.** Let the agent attempt something near-impossible first so the missing tools/skills surface. Then repeat 2–3 more times to shake out edge cases.
4. **Capture before compaction memory is lost.** When the session has compacted 3–4 times, run the capture ritual (exact prompt in `references/capture-ritual.md`) and have it fold everything — small stuff and edge cases — into skill files in a separate folder.
5. **Steer outcomes, not behavior.** Convert the rules you care about into verifiable mechanics: when a pattern is really about "CI check that surfaces x," write the check, then let the model work with full autonomy and let it loop into the check.
6. **Stack the code leverage on reuse.** When re-implementing, tell the model to looks back at prior code/practices — that is the whole compounding effect.
7. **Stop** when the session's knowledge is captured in skills that a next session can load.

## Red Flags

- Writing a spec for a change that "1–2 examples" covers (burn).
- Turning the AGENTS.md into a bible of rules: big overreach affects later runs — keep only small, verifiable exceptions.
- Making markdown artifacts the *source of truth* for code definitions in a fast loop; the chat itself is already an artifact.
- Doing work twice because the small model was left without context that a skill could have supplied.

## Verification

- A captured session produced at least one skill or a reusable change to an existing skill — evidence: `ls ~/.agents/skills` diff, or a `references/` capsule added.
- A rerun of the same class of feature needs visibly less setup prompting than the first run.
- Gates the playbook expected (CI only) actually exist in the project with a real target, not as prose in AGENTS.md.

## Skill Result Contract

```
<skill_result>
  <skill>leverage-playbook</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>capture ritual run; skill/state changes recorded; rerun told contrast</evidence>
  <artifacts>new skill dirs/capsules · AGENTS.md gate changes</artifacts>
  <risks>capture skipped, markdown-written instead of code, gate not wired</risks>
</skill_result>
```

## References

- `references/capture-ritual.md` — the exact capture prompt + source attribution (Tom, 7/26/26)
- `references/outcome-gates.md` — eng principles vs CI-gate conversions (`steer outcomes, not behavior`, Tom, 8/11/26)
- `references/session-principles.md` — prewalk/small-model + "code is ground truth" (Tom, 8/21/26)
