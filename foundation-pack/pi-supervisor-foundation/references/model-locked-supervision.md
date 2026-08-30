<!-- capsule-v2 -->
# Model-locked supervision — model may start supervision once; only the user can change or stop it; goal-append grammar

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you let the agent self-initiate oversight without letting it weaken or redirect that oversight?

## Asymmetric command vs tool authority
**Path/Symbol:** `src/index.ts`: tool guard `startSupervisionFromModel` :93-123; user command `/supervise` handler :342-506; append grammar :470-480; tool schema :511-534.
**Signature:** `startSupervisionFromModel(outcome: string, ctx): Promise<string>` returns refusal text when active; `registerTool({ name:'start_supervision', parameters: Type.Object({ outcome: Type.String({...}) }) })` exposes ONLY outcome — no model/stop parameters.
**Data Shape:** Refusal is a normal string result (tool output the calling model reads), not an exception.

### Decisive source
```ts
    if (state.isActive()) {
      const activeState = state.getState()!;
      return (
        `Supervision is already active and cannot be changed by the model.\n` +
        `Active outcome: "${activeState.outcome}"\n` +
        `Only the user can stop or modify supervision via /supervise.`
      );
    }
```
The user path appends instead of replacing (:470-472):
```ts
      if (state.isActive() && existing) {
        const appendedOutcome = `${existing.outcome}. Additionally: ${trimmed}`;
        state.updateOutcome(appendedOutcome);
```
Model resolution ladder everywhere: `existing?.provider ?? globalModel?.provider ?? sessionModel?.provider ?? 'unknown'`.

**Flow:** model calls start_supervision → inactive? start (with kickstart follow-up if idle) : refusal string → user runs /supervise <goal> while active ⇒ goal EXPANDS by append ("… Additionally: …") never replaces → only `/supervise stop` (user-only) tears down.
**Invariant:** The lock direction matters: the agent can create oversight but never edit/stop it; the user can expand but the original outcome text is preserved verbatim inside the appended string. Tool schema omits model selection entirely ("model cannot be specified" in description) so the supervisor always runs on config/chat-model, not attacker-chosen models.
**Probe:** `grep -c "Only the user can stop or modify supervision" src/index.ts` → 1; `grep -c "existing.outcome}. Additionally: " src/index.ts` → 1. Direct tests: `tests/supervise-command.test.ts:59` "appends to existing goal when supervision is already active", `:288` "should NOT kickstart when appending to existing supervision".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "SupervisorStateManager", query: "updateOutcome start_supervision registerTool", limit: 10 });
```

## Verdict
Adopt the asymmetric-authority pattern for any safety-relevant overseer: initiation allowed from below, modification only from above, expansion-by-append as the compromise for added scope. Adapt the refusal wording and append delimiter. Omit pi's typebox schema shape; keep the minimal-parameter principle.
