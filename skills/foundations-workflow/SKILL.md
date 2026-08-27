---
name: foundations-workflow
description: 'Use when turning one indexed repository into a reusable foundation skill: graph-led seam discovery, source-confirmed implementation capsules, and behavior-tested reuse contracts.'
disable-model-invocation: true
---
# Foundations Workflow

**Code is ground truth; the skill is the retrieval map.** Use Codebase Memory (or `codegraphcontext` when the repo is FalkorDB-indexed locally) to identify a high-leverage connected seam, then confirm the source and direct test that establish its contract. A capsule gives a small model enough code-shaped context to port safely without pretending Markdown replaces the code.

## Core Principle

Code is ground truth; the skill is the retrieval map. A capsule gives a small model enough code-shaped context to port safely without pretending Markdown replaces the code.

## When to Use / NOT

**Use** — turning one indexed repository into a reusable foundation skill: graph-led seam discovery, source-confirmed implementation capsules, and behavior-tested reuse contracts.

**NOT** — claiming completion beyond the graph seam, source range, and test boundary actually confirmed; substituting a coverage census for evidence; inventing a second leaf or reference layout.

## Scope discipline
Work **one source repository and one porting question at a time**. The graph is a navigation and relationship surface—not a checklist for sweeping a repository. Do not claim completion beyond the graph seam, source range, and test boundary actually confirmed.

## Seven acceptance gates
1. **Live index** — project/root/branch/commit/mode/counts/exclusions/freshness.
2. **Graph-led seam selection** — use architecture, graph search, and traces to choose a connected, reusable contract; omit unneeded modules.
3. **Source/test confirmation** — read the decisive source range and its direct test; where a test is unavailable or excluded, state the coverage caveat.
4. **Implementation capsule** — answer one porting question with Source, Path/Symbol, Signature, Data Shape, a labelled decisive source excerpt or pseudocode, Flow, Invariant, direct-test Probe, and graph Retrieve.
5. **Behavior pressure test** — RED without the capsule, GREEN with it, including an adversarial retrieval; no runner means record the block and run deterministic retrieval/probe checks.
6. **Wire** — new leaves are discovered automatically from the filesystem; probe the host skill list to confirm, no manifest or router to update.
7. **Verify** — record direct graph, source, test, coverage, and diff evidence before closing.

## Durable leaf shape
A leaf is a compact capability/source map, not a project ledger or a repo summary. Group only proven capsules by subsystem and end with a short recipe for adding one. Keep optional wave notes and unresolved work in the work record; never substitute a coverage census for evidence.

## Canonical templates
Create every foundation leaf from the canonical loader/map structure and every new or substantively rewritten reference from the canonical capsule-v2 form, both in `references/foundation-templates.md`; the canonical shared copies live at `~/.agents/templates/foundation-skill.md` and `~/.agents/templates/foundation-capsule.md` (template-only library assets, not slash-command render targets). Host mirrors such as `/home/utopia/.dsh/template/work/project/foundation-*.md` are derived copies — fix drift in `~/.agents`, never in a mirror. Do not invent a second leaf or reference layout.

## Capsule versions and stopping rules
`<!-- capsule-v1 -->` remains legacy retrieval metadata. Every **new or substantively rewritten** reference must use `<!-- capsule-v2 -->` and satisfy the decisive-source contract by direct inspection. Keep the canonical pinned commit; do not vendor modules. Stop a wave when its chosen graph seam has a precise retrieval target, decisive source/test evidence, a preserved invariant, and a behavior boundary—not when a repository has been exhaustively described. Volume follows the seam; source excerpt length follows the ambiguity it prevents.

## References

Detailed guidance (load on demand):
- `references/foundation-templates.md` — canonical leaf loader/map structure and capsule-v2 form
- `references/graph-rules.md`
- `references/quality-bar.md`
- `references/skill-anatomy.md`
- `references/squeeze-process.md`
- `references/wiring-verification.md`
- `references/workflow.md`

## Red Flags

Stopping a wave when a repository has been exhaustively described instead of when its chosen graph seam has a precise retrieval target, decisive source/test evidence, a preserved invariant, and a behavior boundary; vendoring modules instead of keeping the canonical pinned commit; a new or substantively rewritten reference still on `<!-- capsule-v1 -->`.

## Verification

Gate 7 — record direct graph, source, test, coverage, and diff evidence before closing. The behavior pressure test is RED without the capsule and GREEN with it (including an adversarial retrieval); with no runner, record the block and run deterministic retrieval/probe checks.

## Skill Result Contract

```
<skill_result>
  <skill>foundations-workflow</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```
