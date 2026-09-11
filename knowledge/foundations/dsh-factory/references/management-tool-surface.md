<!-- capsule-v2 -->
# Management tool surface — how do agents operate the graph through tools without raw store access?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** What is the minimal tool contract that lets an LLM agent create/edit/run graph work safely, and what does the bundled operating skill teach?

## factory_list / create_task / task actions + FACTORY_SKILL
**Path/Symbol:** `packages/tools/src/index.ts` (`apply`, management tools) (:139–381); operating guide text `FACTORY_SKILL` (:130–136); arg builders `automationSpec`/`taskLane` (:28–61).
**Signature:** tools: `factory_list`, `factory_create_task`, `factory_create_flow`, `factory_start_flow`, `factory_update_project`, `factory_adopt_sessions`, `factory_update_task`, `factory_attach_session`, `factory_comment`, `factory_task(action)`; every mutation takes optional `expected_revision`.
**Data Shape:** `managementProjection` strips attachments data URLs and comments to names/counts (context-safe listing); automation args are flat (`automation` mode + `delay_minutes|run_at|cron_expression`) and cross-validated BEFORE any domain call.

### Decisive source
```ts
function automationSpec(mode, delayMinutes, runAt, cronExpression, enabled?) {
    if (mode === undefined) {
      if (delayMinutes !== undefined || runAt !== undefined || cronExpression !== undefined)
        throw new Error('automation is required with timing fields')
      return undefined
    }
    if (mode === 'delay' && delayMinutes === undefined) throw new Error('delay_minutes is required for delay automation')
    ...
}
```
plus the skill's load-bearing rules: "Hard deletion is intentionally unavailable: cancel work to preserve its audit history", "Do not claim success from intent alone", "Publishing and cleanup belong in explicit graph tasks".

**Flow:** agent calls a tool → cwd-scoped project resolution (workspace = calling session's cwd) → flat args cross-validated (mode↔timing-field pairing, lane↔baseRef/reuseTaskId pairing, at-least-one-mutable-field for updates) → domain Remote call with expected_revision for optimistic concurrency → response echoes canonical identifiers/status. The bundled skill registers itself so ANY session knows the operating rules.
**Invariant:** Validation happens in the TOOL layer before the domain sees the request — the domain's thrown errors are the backstop, not the first line; read-only `factory_list` declares itself concurrency-safe and exposes NO secret payloads (attachment bytes stripped). No delete tool exists BY DESIGN.
**Probe:** `packages/tools/tests/management.spec.ts` "rejects incomplete one-time or recurring automation and empty task updates before mutation" + "lists complete task, flow, run, and live Session management identities without patterns". Deterministic from repo root: `grep -c 'automation is required with timing fields' packages/tools/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "managementProjection", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt the two-layer validation split and the audit-preserving no-delete doctrine. Adapt tool framework and naming. Omit presentCall card metadata.
