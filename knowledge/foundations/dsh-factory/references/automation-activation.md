<!-- capsule-v2 -->
# Automation activation — how do delayed/scheduled/recurring prompts queue exactly when due?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How does a scheduler turn stored automation specs into queued tasks without overlap, premature firing, or lost recurrences?

## activateTaskAutomations
**Path/Symbol:** `packages/domain/src/mutations.ts` (`activateTaskAutomations`, `taskAutomation`) (:66–124).
**Signature:** `function activateTaskAutomations(document, now: string): { changed: boolean; activated: FactoryTask[] }`; `taskAutomation(spec, defaultEnabled, now)` validates at write time.
**Data Shape:** trigger kinds `manual|delay|schedule|recurring`; per-task `nextRunAt?: string`; delay tasks require ALL dependencies succeeded and base their timer on the LATEST dependency's updatedAt; recurring requires status exactly `scheduled` to re-arm.

### Decisive source
```ts
const recurring = automation.trigger.kind === 'recurring'
if (recurring ? task.status !== 'scheduled' : task.status !== 'draft') continue
...
const baseMs = dependencies.length === 0
    ? Date.parse(task.updatedAt)
    : Math.max(...dependencies.map(dependency => Date.parse(dependency.updatedAt)))
nextRunAt = new Date(baseMs + automation.trigger.delayMinutes * MINUTE_MS).toISOString()
...
if (Date.parse(nextRunAt) > nowMs) continue
task.status = 'queued'
if (automation.trigger.kind === 'recurring') automation.nextRunAt = nextFactoryRecurringRun(automation.trigger.schedule, new Date(now))
else { automation.enabled = false; delete automation.nextRunAt }
delete task.failure
delete task.output
```

**Flow:** each activation sweep (called by the leader pump before claiming): recurring tasks only fire from `scheduled`, one-shots only from `draft` → compute nextRunAt if missing (delay = max dependency updatedAt + delayMinutes; schedule = its ISO at; recurring = next occurrence after updatedAt) → due? → queue the task, clear failure/output, advance recurrence to next future run OR kill the one-shot → domain wraps this in a store mutation and appends activity.
**Invariant:** Status gates make firing IDEMPOTENT — an already-queued/running task can't double-fire because it's no longer in the gate status; one-shot automations self-disable on fire so they can't repeat; clearing failure/output at activation gives each occurrence a clean slate while Triage keeps PAST runs' outputs.
**Probe:** `packages/domain/tests/domain.spec.ts` "queues one-shot scheduled and dependency-delayed prompts only when due" (not-due stays draft; due queues once) and "runs recurring tasks repeatedly, retains Triage results, and never completes the schedule". Deterministic from repo root: `grep -c 'MAX_AUTOMATION_DELAY_MINUTES' packages/domain/src/mutations.ts` = 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "activateTaskAutomations", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt status-gated idempotent activation + latest-dependency delay basing + one-shot self-disable. Adapt the cadence vocabulary. Omit nothing else.
