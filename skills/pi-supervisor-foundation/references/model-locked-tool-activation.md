<!-- capsule-v2 -->
# Model-locked tool activation — how can the AGENT start supervision but never change or stop it?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What exact guard makes model-initiated supervision one-way, and why is the model parameter forbidden?

## start_supervision tool (`src/index.ts:509-535` + `startSupervisionFromModel` :93-123)
**Path/Symbol:** `src/index.ts:pi.registerTool({name:'start_supervision'})` (:511-534); shared entry `startSupervisionFromModel(outcome, ctx)` (:93-123).
**Signature:** `execute(toolCallId, params:{outcome:string}, signal, onUpdate, ctx)`; schema via TypeBox `Type.Object({outcome: Type.String(...)})`.
**Data Shape:** Returns a text content block with one of two verdict strings: already-active refusal or `Supervision active. Outcome: "..."`.

### Decisive source
```ts
const startSupervisionFromModel = async (outcome, ctx) => {
  if (state.isActive()) {
    const activeState = state.getState()!;
    return `Supervision is already active and cannot be changed by the model.\n` +
           `Active outcome: "${activeState.outcome}"\n` +
           `Only the user can stop or modify supervision via /supervise.`;
  }
  const globalModel = loadGlobalModel();
  const provider = globalModel?.provider ?? sessionModel?.provider ?? 'unknown';
  state.start(outcome, provider, modelId);       // NO model param accepted
  if (ctx.isIdle()) pi.sendUserMessage(`Please start working on this goal: ${outcome}`,
                                       { deliverAs: 'followUp' });
```

**Flow:** tool call → active? refuse with the ACTIVE outcome echoed back → else resolve supervisor model from config-ladder (active-state > global config `.pi/supervisor-config.json` > chat model) — the requesting model CANNOT nominate itself or another model → start + persist → idle kickstart prompt.
**Invariant:** (1) Asymmetry by construction: the same `state.start()` is reachable from user command AND agent tool, but modification/stop are NOT on the tool — once locked, only `/supervise stop|model` (user) can change anything. (2) Model choice is resolved from USER-controlled sources only, preventing an agent from pointing the judge at a compliant model. (3) The refusal message quotes the live outcome — the agent learns the constraint without a side channel.
**Probe:** `tests/supervise-command.test.ts` goal-append suite (:46-118: append updates outcome while active); refusal text pinned at `src/index.ts:100-103` (`grep -c "cannot be changed by the model" src/index.ts` = 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "start_supervision registerTool cannot be changed by the model", limit: 8 });
```

## Verdict
Adopt start-only tool surface + config-ladder model resolution for any "agent may request oversight" feature. Adapt the TypeBox schema to your host's tool definition. Omit pi's sendUserMessage kickstart if your host lacks queued follow-ups.
