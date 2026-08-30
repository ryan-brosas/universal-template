---
name: code-foundations
description: 'Use when deciding where reusable implementation knowledge should live: a useful repository becomes project-local reference code; only repeated, non-obvious porting knowledge may become a compact foundation skill.'
disable-model-invocation: true
---
# Code Foundations

Code and tests are ground truth. The default home for a useful repository is project-local reference code — read there, not in Markdown. A foundation is the selective exception: a compact retrieval map for repeated, non-obvious porting knowledge that source alone does not surface.

## Core Principle

Code and tests are ground truth; a foundation is a compact retrieval map, not a re-description — it never vendors modules.

## When to Use / NOT

- **Use when:** a proven code pattern, primitive, or integration is worth reusing — recurring, proven (working + tested), and reusable beyond the feature that introduced it.
- **NOT when:** the implementation is speculative or one-off; never encode those.

## Workflow

Run the code-grounded loop: discover (Fovea on the active or reference root; Codebase Memory to find which persistent-library project holds the pattern) → confirm (read exact source, pin commit+branch+license) → encode (point to code first, add porting context) → verify (source test or direct probe) → route (leaf only for a new reusable trigger).

## Reference first

A useful repository is normally used as **reference code**, not encoded:
place it at `<project>/reference/<repo>/` (read-only prior art), map it with
Fovea when helpful, read the actual source and direct tests, then adopt /
adapt / omit. A reference is disposable evidence — not automatically a skill,
a Codebase Memory project, or an OpenViking resource. Keep local-only
references out of commits via `.git/info/exclude` where appropriate; respect
licenses when materially copying implementation. Canonical contract:
`references/reference-contract.md`.

**Freeze:** new repo-derived foundations are paused while the reference-driven
workflow is validated. Foundation generation is a deliberate exception path
(`foundations-workflow`, run per repository by `memory-graph-skill-miner`),
never the automatic destination for a useful repo.

## When to encode
A foundation is worth creating only when the reusable knowledge is **repeated, non-obvious porting knowledge** — a recurring wrong-port pattern, a hard-won invariant, a proven capsule that demonstrably changed an outcome. A useful repository alone is no longer sufficient. Never encode speculative or one-off implementations.

**Promotion rule for new foundations:** recurring need (not one-off) · the source implementation works · relevant behavior is tested or probed · provenance is pinned (repo, commit/branch, license) · the shortcut has already been useful more than once or has a clear recurring use case · source/tests remain the authority · the capsule is materially smaller than the implementation knowledge it points to. Where practical, require the consuming agent to reopen the actual source before porting.

## Capsule content boundary

**A foundation is a retrieval shortcut to proven code, not a substitute reconstruction of the implementation.**

- Keep (retrieval metadata): upstream repo, pinned commit/branch, license, exact path + symbol, direct test/probe, the invariant that prevents a bad port, the CodeMemory retrieval query/project, and known porting hazards.
- Question (derived implementation prose): long algorithm retellings, equations copied into summaries, extensive data-flow reconstruction, and internal behavior already readable in accessible source. Keep derived prose only when it demonstrably prevents a recurring wrong implementation and the source pointer alone is insufficient.

## The code-grounded loop
1. Discover - use Fovea on the active/reference root (or Codebase Memory across the persistent library) to find the symbol, its callers, tests, and coverage.
2. Confirm - read exact source/excluded tests for each claim; pin commit+branch+license.
3. Encode - point to code first, then add code-shaped porting context that blocks wrong reuse.
4. Verify - keep a source test or direct probe; no behavior boundary, no foundation.
5. Route - add a leaf only for a new reusable trigger; never copy a whole repo into Markdown.

## Implementation capsules
A capsule contract answers one porting question with Path/Symbol, Signature, Data Shape, Flow, Invariant, Probe, Retrieve. Short interfaces/state/pseudocode belong only when the path+signature alone would let a small model port the wrong shape.
## Rules
- One active inspiration repo at a time; finish evidence + verification before the next project.
- Placement: foundation leaves stay in the flat `skills/` namespace — pi (native discovery), the Claude/Codex/OpenCode mounts, and the catalog validators all assume `skills/*/SKILL.md`. What separates a foundation from a procedure skill is the semantic boundary above, not the directory.
- Proven only; adopt/adapt/omit; pin provenance + coverage caveats.
- Constants/examples only when they change the decision.
- Prefer a short direct test probe over a long behavioural explanation.

## Legacy triage (existing *-foundation leaves)

Do not mass-delete. Triage each leaf:

- **Keep:** source pointers, pinned provenance, direct tests/probes, license, recurring porting hazards, non-obvious invariants, known wrong-port patterns, genuinely hard-won synthesis.
- **Shrink/retire:** repository-wide summaries, detailed algorithm reconstructions, information cheaply recoverable from the actual repo, copied equations/data-flow narratives, huge Markdown descriptions.
- **Order of operations:** prove the replacement first (reference repo + Fovea + direct tests), then shrink. First audit target: `framer-motion-foundation` (a large implementation-knowledge package whose reference repo + Fovea + tests likely cover most of it). No deletion until the reference-driven strategy works on real tasks.

## Verification
Every public line routes to a tested symbol + a named probe; capsule refs pass direct wiring and loader/map inspection; `git diff --check` is clean.

## Red Flags

- Encoding speculative or one-off implementations.
- Copying a whole repo into Markdown.
- A foundation without a behavior boundary or probe.
- More than one active inspiration repo at a time.
- Provenance unpinned (commit/branch/license missing).

## Skill Result Contract

```
<skill_result>
  <skill>code-foundations</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Every public line routes to a tested symbol + named probe; git diff --check clean</evidence>
  <artifacts>Foundation leaf with capsules (Path/Symbol, Signature, Data Shape, Flow, Invariant, Probe, Retrieve)</artifacts>
  <risks>Speculative encoding, missing probe, unpinned provenance, or none</risks>
</skill_result>
```

## References

N/A — no reference files; this skill is self-contained.
