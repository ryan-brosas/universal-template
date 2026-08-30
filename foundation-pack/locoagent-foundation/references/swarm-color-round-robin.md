<!-- capsule-v2 -->
# Teammate color round-robin — how are UI colors assigned without collisions or reassignment?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what is the complete lifecycle of a teammate's display color, and why does the layout manager refuse to cache backends?

## assignTeammateColor idempotent-by-id + clearTeammateColors reset
**Path/Symbol:** `src/utils/swarm/teammateLayoutManager.ts:assignTeammateColor` (:22-33), `getTeammateColor` (:38-42), `clearTeammateColors` (:48-51), `getBackend` (:14-16).
**Signature:** `assignTeammateColor(teammateId: string): AgentColorName` — `AGENT_COLORS[colorIndex % AGENT_COLORS.length]`.
**Data Shape:** module Map<teammateId, AgentColorName> + monotonically increasing colorIndex.

### Decisive source
```ts
export function assignTeammateColor(teammateId: string): AgentColorName {
  const existing = teammateColorAssignments.get(teammateId)
  if (existing) {
    return existing
  }
  const color = AGENT_COLORS[colorIndex % AGENT_COLORS.length]!
  teammateColorAssignments.set(teammateId, color)
  colorIndex++
  return color
}
```
Backend note (:12): "detectAndGetBackend() caches internally — no need for a second cache here."

**Flow:** PaneBackendExecutor.spawn calls assignTeammateColor ONLY when config didn't pin one (`config.color ?? assignTeammateColor(agentId)`) → repeat calls for the same id return the SAME color (idempotence guard before index consumption) → team cleanup calls clearTeammateColors resetting BOTH map and index so a new team restarts the palette → tmux-side mapping translates palette names to tmux color syntax (purple→magenta, orange→colour208, pink→colour205 — TmuxBackend getTmuxColorName).
**Invariant:** assignment must be check-then-maybe-consume — consuming an index on every call would rotate a stable teammate's color; explicit user-specified colors bypass rotation entirely and never occupy palette slots.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'no need for a second cache here' src/utils/swarm/teammateLayoutManager.ts`; `grep -n 'colour208' src/utils/swarm/backends/TmuxBackend.ts` (:66).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "assignTeammateColor clearTeammateColors AGENT_COLORS", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt idempotent round-robin resource assignment with explicit wholesale resets between team generations; adapt palettes; omit if your UI has no per-agent identity colors.
