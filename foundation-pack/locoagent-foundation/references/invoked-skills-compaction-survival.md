<!-- capsule-v2 -->
# invoked-skills compaction survival — how does "the agent already ran this skill" survive a context compaction?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Skill-invocation records must outlive compaction (so the model doesn't re-read or re-run a skill) yet stay scoped per subagent and cleanable per team — what's the keying and clearing contract?

## addInvokedSkills family: composite `${agentId}:${skillName}` keys + preservation-set clears
**Path/Symbol:** `src/bootstrap/state.ts`:`invokedSkills` comment (`:176-187`), `InvokedSkillInfo` (`:1502-1508`), `addInvokedSkill` (`:1510-1524`), `getInvokedSkillsForAgent` (`:1530-1541`), `clearInvokedSkills(preservedAgentIds?)` (`:1543-1555`), `clearInvokedSkillsForAgent` (`:1557-1563`).
**Signature:** `addInvokedSkill(skillName: string, skillPath: string, content: string, agentId: string | null = null): void`; `getInvokedSkills(): Map<string, InvokedSkillInfo>`; `getInvokedSkillsForAgent(agentId: string | undefined | null): Map`; `clearInvokedSkills(preservedAgentIds?: ReadonlySet<string>): void`.
**Data Shape:** Value `{ skillName, skillPath, content, invokedAt, agentId }`. Key is the COMPOSITE `` `${agentId ?? ''}:${skillName}` `` — null agent maps to the EMPTY prefix so main-agent entries are addressable too.

### Decisive source
```ts
// :177 — the load-bearing key format
// Keys are composite: `${agentId ?? ''}:${skillName}` to prevent cross-agent overwrites
// :1516
const key = `${agentId ?? ''}:${skillName}`
// :1543-1555
export function clearInvokedSkills(preservedAgentIds?: ReadonlySet<string>): void {
  if (!preservedAgentIds || preservedAgentIds.size === 0) {
    STATE.invokedSkills.clear()                       // full clear (no team context)
    return
  }
  for (const [key, skill] of STATE.invokedSkills) {
    if (skill.agentId === null || !preservedAgentIds.has(skill.agentId)) {
      STATE.invokedSkills.delete(key)                 // keep ONLY preserved agents'
    }
  }
}
```

**Flow:** skill invocation → record content+path under composite key → compaction happens → post-compaction prompt rebuild re-injects invoked-skill contents from this map instead of letting the model guess → teammate/agent exits → `clearInvokedSkills(preservedAgentIds)` keeps surviving teammates' entries and drops everyone else's (main-agent entries with `agentId === null` always die on a scoped clear).
**Invariant:** WITHOUT the agent-scoped composite key, two agents running the same skill overwrite each other's record and one loses its compaction anchor. The value stores full CONTENT (not just a path) because the file may change/be unavailable post-compaction; what was injected THEN is what gets replayed. Clearing is three distinct operations — everything / everything-except-preserved-agents / one-agent — matching the three lifecycle events (session end, team shrink, single teammate exit). Note the asymmetry: `clearInvokedSkillsForAgent(agentId)` matches EXACT ids while the scoped clear treats `null` as disposable.
**Probe:** Deterministic pins: `grep -n 'prevent cross-agent overwrites' src/bootstrap/state.ts` → `177:`; `grep -n 'preserved across compaction' src/bootstrap/state.ts` → `176:`; `grep -n 'agentId ?? ' src/bootstrap/state.ts | head -1` → `1516:  const key = \`\${agentId ?? ''}:\${skillName}\``; `grep -n 'skill.agentId === normalizedId' src/bootstrap/state.ts` → `1536:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "invoked skills compaction preserve addInvokedSkill", limit: 10 });
```

## Verdict
Adopt composite-keyed invocation ledgers storing full content for anything that must survive context summarization. Adapt the key separator to your ID alphabet (avoid collision if agent IDs can contain your separator), and mirror the three-clear lifecycle. Omit `invokedAt` unless you add TTL eviction.
