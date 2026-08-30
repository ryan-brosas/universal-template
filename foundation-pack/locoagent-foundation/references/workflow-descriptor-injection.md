<!-- capsule-v2 -->
# Workflow descriptor → registry-injected executor config — how do pipeline definitions stay free of connection info while executors still receive port/profile/device?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a scheduler spawns browser pipelines from declarative JSON definitions, where do the CDP port, profile dir, proxy, and device live — in every definition (drift), in the environment (invisible), or injected from one registry at spawn time?

## Path/Symbol
`scripts/workflow-engine.ts`: `loadWorkflowDefinitions` (`:83-91`), `getWorkflowDef` (`:93-96`), `buildConfigJson` (`:104-116`), `WorkflowDefinition` interface (`:33-40`); `STATE_PATH = resolve(WORKFLOWS_DIR, 'state.json')` (`:30`). Executor-side consumer: `workflows/executors/x-search-reply.ts` `--config` argv scan (`:38-43`). Concrete descriptor instances on disk: `workflows/{x-search-reply,hf-papers-to-x,hf-daily-papers,linkedin-search-reply}.json`.

**Signature:** `buildConfigJson(def: WorkflowDefinition): string`; `loadWorkflowDefinitions(): WorkflowDefinition[]`.

**Data Shape:** Descriptor = `{ id, name, description, schedule, platform?, executor, config: Record<string, unknown> }`. Spawn arg = `--config <single JSON string>` (one argv token, not two). Merged shape seen by the executor = `{ ...def.config, platform, cdpPort, profile, device, proxy? }`. State lives separately: `StateFile = { version: 1, workflows: Record<id, { status, lastRun, runCount, history }> }`.

### Decisive source
```ts
function loadWorkflowDefinitions(): WorkflowDefinition[] {
  const files = readdirSync(WORKFLOWS_DIR).filter(
    f => f.endsWith('.json') && f !== 'state.json'
  )
  return files.map(f => {
    const content = readFileSync(resolve(WORKFLOWS_DIR, f), 'utf-8')
    return JSON.parse(content) as WorkflowDefinition
  })
}

/**
 * Build the --config JSON for an executor. When the workflow declares a platform,
 * the resolved target's cdpPort/profile/proxy/device are injected so the port
 * lives in exactly one place (the registry). Workflows without a platform fall
 * back to their own config (back-compat).
 */
function buildConfigJson(def: WorkflowDefinition): string {
  if (!def.platform) return JSON.stringify(def.config)
  const t = resolveTarget(def.platform)
  const merged: Record<string, unknown> = {
    ...def.config,
    platform: def.platform,
    cdpPort: t.cdpPort,
    profile: t.profile,
    device: t.device,
  }
  if (t.proxy) merged['proxy'] = t.proxy
  return JSON.stringify(merged)
}
```

## Flow
1. Engine startup / any command: `readdirSync(workflows/)` → keep `*.json` **except `state.json`** → parse each as a `WorkflowDefinition`. Definitions are re-read on every lookup (no cache) — editing a descriptor takes effect on the next command with zero reload step.
2. `start`/`run`: `prepareRun` resolves def + state + executorPath and calls `buildConfigJson(def)` (`:208`); the detached spawn passes it as ONE argv pair: `Bun.spawn(['bun','run', executorPath, '--config', buildConfigJson(def)])` (`:289`); the synchronous `run` path builds the same string (`:590`).
3. Registry resolution: `resolveTarget(def.platform)` (browser-targets capsule) turns `platform: "x"` into the canonical `cdpPort/profile/proxy/device` — the same resolution the doctor and bring-up use.
4. Merge order is deliberate: `...def.config` first, registry values after — **registry wins** any accidental collision.
5. Executor side receives it by scanning argv backwards (`configArg = process.argv.find((_, i, a) => a[i-1] === '--config')`) then `JSON.parse(configArg)`; it reads the injected `platform` too (e.g. building `--session` flags from `config.platform`).

**Invariant:** The CDP port lives in EXACTLY ONE place — the browser-targets registry. Descriptors carry product knobs only (search query, username, output dir, prompts); a porter who copies the port into a workflow JSON breaks the single-source invariant and the doctor/engine silently diverge. Two structural guards: (a) `state.json` sits INSIDE `workflows/` and must be excluded from the definition glob or it parses as a bogus WorkflowDefinition; (b) `platform`-less workflows bypass injection entirely (their own config is the whole payload) — that back-compat branch is also the escape hatch for non-browser pipelines.

## Probe
No direct unit test covers `workflow-engine.ts` (coverage caveat — source-grounded probe; `browser-targets.test.ts` covers the `resolveTarget` half). Deterministic checks: grep pins `f !== 'state.json'` at `scripts/workflow-engine.ts:85`, `resolveTarget(def.platform)` at `:107`, and the spread-order merge at `:108-115`; `workflows/x-search-reply.json` on disk shows a real descriptor whose `config` block carries NO `cdpPort`/`profile` keys while its `platform: "x"` drives injection.

**Retrieve:** `search_graph --project locoagent --query "buildConfigJson"` → `locoagent.scripts.workflow-engine.buildConfigJson` Function `scripts/workflow-engine.ts 104-116`; `trace_path --function-name buildConfigJson --direction both` → callers `prepareRun`/`executeWorkflow`, callees `resolveTarget`/`loadTargets`/`parseRegistry`/`resolveEntry`.

**Verdict:** Adopt. The inject-at-spawn pattern ports to ANY scheduler that runs declarative pipeline definitions against shared singleton resources (browsers, devices, DB schemas): definitions describe WHAT to run; a registry owns WHERE/HOW to connect; the engine stitches them at spawn.
