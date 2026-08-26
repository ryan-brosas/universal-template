---
name: development-lifecycle
description: Use when starting, planning, shipping, or verifying a work session — describes how `/create`, `/plan`, `/ship`, `/verify`, and `/research` interact with the canonical work artifacts under `.pi/work/`.
disable-model-invocation: true
---


# Development Lifecycle

## Canonical Artifact Files

At the active work record `.pi/work/$(cat .pi/work/.active)/`, maintained in the working copy:

| File              | Purpose                                   | Use when                                          |
|-------------------|-------------------------------------------|---------------------------------------------------|
| `spec.md`         | PRD/spec (Spec-Driven mode only)        | `/create` |
| `tasks.md`        | Task list from spec or codebase         | `/create` |
| `plan.md`         | Implementation plan and slice ordering    | `/plan`                                           |
| `research.md`     | Exploration notes and evidence            | `/research`                                       |
| `verification.md` | Verification evidence per gate run        | `/verify`                                         |
| `adr.md`          | ADRs (Architecture Decision Records)      | Real trade-off between two or more viable options |
| `.progress.md`    | Per-iteration log: tried, failed, learned | Long-running investigation or build               |

Codebase-driven records (default) skip spec.md; the session is the artifact.

**Entry format (tasks.md, .progress.md):** `### YYYY-MM-DD - <title>` followed by `status: active | done | abandoned | updated: <date>`.

## Slash Commands (Lifecycle Hooks)

- `/create <idea>` — turn a rough idea into `issue.md` + `tasks.md` (plus `spec.md` in Spec-Driven mode, and optional `proposal.md`, `design.md`, `adr.md`). Loaded from `brainstorming` + `spec-driven-development`.
- `/plan` — open / resume the current plan (`plan.md`). Loaded from `planning-and-task-breakdown`.
- `/ship` — implement the active record end to end; run the canonical gate. Loaded from `shipping-and-launch`.
- `/verify` — claim-completion evidence gate (`verification.md`, `.verify.log`). Loaded from `verification-before-completion`.
- `/research` — exploratory investigation; lives in `research.md`. Loaded from `spec-driven-development`.

## Workflow

```
   /create  ──>  /plan  ──>  implement  ──>  /ship  ──>  /verify
      │            │           │              │           │
   spec.md*    plan.md      .progress.md   spec.md*    verification.md
   tasks.md    updates      updates      implemented  evidence
```

* `spec.md` is Spec-Driven mode only.

**`/research` is sideways** — it feeds `/plan` or `/create`, not the linear path.

## When to Use Each Phase

| Phase       | Trigger                             | Skip if                                   |
|-------------|-------------------------------------|-------------------------------------------|
| `/create`   | New feature / product / record       | Trivial one-liner                         |
| `/plan`     | Multi-file change, ambiguous spec   | Single known file, clear spec             |
| `/ship`     | Before merge / commit               | No code change this session               |
| `/verify`   | Before "done" claim, always         | Never skip                                |
| `/research` | Open-ended question, no answer path | The answer is in the code or docs already |

## Lifecycle Rules

1. **No silent skipping** — if you skip a phase, name it ("skipped /plan: single-file fix").
2. **Update tasks.md first, then code** — append the entry before the first edit. Re-reading it on resume gives you the state.
3. **.progress.md = investigation log** — failed attempts and "what I tried" go here, not in chat.
4. **adr.md is for trade-offs, not choices** — if there's only one viable option, it goes in plan.md as a fact, not an ADR.
5. **/verify is non-negotiable** — every "done" claim cites evidence.

## Red Flags

- tasks.md has no `### YYYY-MM-DD - <title>` entries — likely stale or skipped.
- .progress.md empty on a multi-hour task — context loss on resume.
- adr.md used as a dumping ground for any choice — noise, not signal.
- "Done" claim without `/verify` evidence — common regression.

## Pi Fabric Boundaries

**Discovery** — Pi Fovea before text search. **Mutation** — file writes defer to the Schema mutation guard in AGENTS.md. **Verification** — direct behavioral probes with recorded output.

## Skill Result Contract

```xml
<skill_result>
  <skill>development-lifecycle</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Phase(s) used named, artifact files updated, /verify evidence cited</evidence>
  <artifacts>paths touched under .pi/work/&lt;id&gt;/</artifacts>
  <risks>Skipped phases, stale entries, or none</risks>
</skill_result>
```
