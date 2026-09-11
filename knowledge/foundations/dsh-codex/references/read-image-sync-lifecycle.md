<!-- capsule-v2 -->
# Read-image shadow lifecycle — synchronize one enhancement per live agent

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should a live plugin install and remove an enhanced read_image shadow across agent, tool, and policy changes without duplicate wrappers or teardown leaks?

## installReadImageEnhancement
**Path/Symbol:** src/read-image-enhancement.ts:172-223 installReadImageEnhancement, including remove, syncAgent, and syncAll.
**Signature:** installReadImageEnhancement(ctx: Context, policy: ImageToolPolicy, publicHttpRuntime?: PublicHttpRuntime): void.
**Data Shape:** A private Map<Agent, ScopedEnhancement> records the original tool identity and its disposer. A syncing latch prevents re-entrant whole-fleet passes; policy/tool/agent events trigger targeted or full synchronization.

### Decisive source
~~~ts
const installed = new Map<Agent, ScopedEnhancement>()
let syncing = false
if (!policy.snapshot().modifyReadImage || original === undefined) {
  remove(agent)
  return
}
if (current?.original === original) return
if (current !== undefined) remove(agent)
if (ctx.tools.get(READ_IMAGE_TOOL_NAME, agent) !== original) return
const dispose = agent.ctx.tools.register(enhancedReadImageTool(ctx, original, publicHttpRuntime))
installed.set(agent, { original, dispose })
ctx.on('agent/created', ({ agent }) => { syncAgent(agent) })
ctx.on('agent/disposed', ({ agent }) => { installed.delete(agent) })
ctx.on('tools/change', syncAll)
const stopPolicy = policy.watchImagePreferences(syncAll)
ctx.effect(() => () => {
  stopPolicy()
  for (const agent of [...installed.keys()]) remove(agent)
}, 'dsh-openai-codex: enhanced read_image')
~~~

**Flow:** maintain identity-keyed installation records, remove stale shadows before replacing an original tool, refuse to wrap an agent override, react to new/disposed agents and tool/policy changes, and dispose the watcher plus every registered shadow from the host effect.
**Invariant:** disabled policy removes shadows; unchanged original tools are not double-wrapped; a shadow is installed only when the agent still exposes the same original tool; re-entrancy is suppressed; host teardown removes every disposer and stops the policy watcher.
**Probe:** tests/tool-policy.spec.ts:63-79 executes the live image-preference watcher and observes exactly one change; tests/read-image-enhancement.spec.ts:127-165 exercises the enhanced tool behavior used by the installer. A dedicated installReadImageEnhancement lifecycle test is absent, so the registration identity/order/cleanup claims are source-confirmed via the live graph snippet and exact source range, not promoted to direct behavioral coverage.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.read-image-enhancement\\.installReadImageEnhancement', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt identity-keyed shadow registration, re-entrancy protection, event-driven resync, and effect-owned cleanup. Adapt agent/tool/effect APIs and policy watcher names; retain the no-double-wrap and no-agent-override rules. Omit global replacement of the original tool or teardown that only drops listeners. Coverage caveat: source and graph are covered with metadata_match, policy/behavior boundaries pass the direct suite, but the installer itself lacks a dedicated direct test.
