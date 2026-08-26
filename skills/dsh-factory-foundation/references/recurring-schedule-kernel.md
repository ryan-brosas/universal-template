<!-- capsule-v2 -->
# Recurring schedule kernel — how do friendly cadences compile to cron and never double-fire?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I validate/normalize recurring schedules, compute strictly-after next runs, and hand back the exact nextRunAt so recurring tasks survive crashes?

## normalize / nextFactoryRecurringRun / factoryRecurringCron
**Path/Symbol:** `packages/domain/src/schedule.ts` (:11–56) + `packages/protocol/src/schedule.ts` (`factoryRecurringCron`, `factoryRecurringLabel`) (:7–31).
**Signature:** `normalizeFactoryRecurringSchedule(schedule): FactoryRecurringSchedule`; `nextFactoryRecurringRun(schedule, after: Date): string`; `factoryRecurringCron(schedule): string`.
**Data Shape:** six friendly kinds (`hourly|daily|weekdays|weekly|monthly|cron`); cron alias regex `/^@(annually|yearly|monthly|weekly|daily|midnight|hourly)$/u`; delay automations capped at 10_080 minutes (one week) in mutations.ts.

### Decisive source
```ts
case 'cron': {
    const expression = schedule.expression.trim().replaceAll(/\s+/gu, ' ')
    if (expression.length === 0 || expression.length > 256 || (!CRON_ALIAS.test(expression) && expression.split(' ').length !== 5))
      throw new Error('Factory cron must be a supported alias or five fields')
    normalized = { kind: 'cron', expression }
    break
}
...
nextFactoryRecurringRun(normalized, new Date())   // validation = must have a future occurrence
return normalized

export function nextFactoryRecurringRun(schedule: FactoryRecurringSchedule, after: Date): string {
  let next: Date | null
  try { next = new Cron(factoryRecurringCron(schedule), { paused: true }).nextRun(after) }
  catch (error) { throw new Error(`Factory recurring schedule is invalid: ...`) }
  if (next === null) throw new Error('Factory recurring schedule has no future occurrence')
  return next.toISOString()
}
```

**Flow:** normalize validates every field (weekday dedupe+sort, hourly minute 0-59, monthly day 1-31; cron whitespace-collapsed to five fields OR a known @-alias) and PROVES it by computing one next run at validation time → activation stores `nextRunAt` explicitly → after a terminal run, `activateTaskAutomations` advances recurring tasks to `scheduled` with a FRESH nextRunAt computed from now (never from the stale stored value), while one-shot triggers disable themselves.
**Invariant:** Validation-by-execution (a schedule that can't produce a future occurrence is invalid input, not a runtime surprise); next runs are STRICTLY AFTER the reference instant (no same-instant refire); paused-mode Cron instances are used purely as calculators — no timers are created by the domain layer.
**Probe:** `packages/protocol/tests/graph.spec.ts` "derives Scheduled flows and compiles every friendly recurring cadence" (pins `'15 * * * *'`, `'30 9 * * *'`, `'0 8 * * 1-5'`, weekly dedupe `[5,1,1]→'5 10 * * 1,5'`, `'45 7 12 * *'`, label `'Cron: */15 * * * *'`). Deterministic from repo root: `grep -c 'paused: true' packages/domain/src/schedule.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "factoryRecurringCron", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt normalize-with-proof + strictly-after next-run computation + explicit nextRunAt persistence. Adapt the cron library (croner here). Omit the UI label formatter if host has no card surface.
