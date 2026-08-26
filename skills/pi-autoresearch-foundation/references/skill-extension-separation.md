<!-- capsule-v2 -->
# Skill/extension separation — where does domain knowledge end and loop infrastructure begin?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** Why is the loop split into extension + skill, and what does the skill own that code must not?

## autoresearch-create SKILL.md — one extension serves unlimited domains via two authored files
**Path/Symbol:** `skills/autoresearch-create/SKILL.md` (frontmatter description triggers on "run autoresearch"/"optimize X in a loop"); package manifest wires both: `package.json` `"pi": {"extensions": ["./extensions"], "skills": ["./skills"]}`; architecture table README :184–197.
**Signature:** workflow: gather (goal, command, metric±direction, target, scope, constraints) → `activate` → author `autoresearch.md` (session doc: objective/metrics/scope/tried) + `autoresearch.sh` (pre-checks; workload; `METRIC name=value` lines) → `init` → baseline → log → loop forever.
**Data Shape:** optional third file `autoresearch.checks.sh` (backpressure). The skill ALSO encodes when NOT to use it: <10 iterations, sub-second feedback, or trivial changes ⇒ plain bash/edit instead.

### Decisive source
```md
The **extension** is domain-agnostic infrastructure. The **skill** encodes
domain knowledge. This separation means one extension serves unlimited domains.
```
(README "How it works"; mirrored by the skill's Workflow section which instructs the agent to WRITE the benchmark script rather than pick from a registry.)

**Flow:** user says "optimize test runtime" → skill prompt gathers/infers config → agent authors autoresearch.sh emitting METRIC lines → harness run-lock (see autoresearch-sh-run-lock capsule) enforces all future benchmarks go through that script → every keep commits the script+code together so history stays reproducible. ASI free-form keys (`hypothesis`, `next_action_hint`, `rollback_reason`) are CONVENTIONS taught by the skill and surfaced by compaction formatting — no schema enforcement anywhere in code.
**Invariant:** infrastructure never hardcodes a metric/command/domain (the only domain string in code is the filename prefix `autoresearch.`); the skill never reimplements state (it drives CLI verbs only). This boundary is why the same binary optimizes test speed, bundle size, Lighthouse, or training loss with zero code changes.
**Probe:** anchors: `grep -c 'METRIC ' skills/autoresearch-create/SKILL.md` ≥1 (grammar taught to the authoring agent); `grep -n '"pi"' -A3 package.json` → extensions+skills wiring; direct tests `__tests__/unit/tools.test.ts` + `__tests__/unit/platform.test.ts` cover the tool-name surface the skill invokes.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "skill extension separation autoresearch-create workflow activate init", limit: 10 });
```

## Verdict
Adopt the infra/domain split verbatim when building any autonomous loop for an LLM agent: code owns state/git/statistics, prose owns goal-interpretation and benchmark authorship. Coverage caveat: SKILL.md content is source-pinned (not machine-tested); its CLI verb list matches cli.ts exactly as of this pin.
