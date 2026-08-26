<!-- capsule-v2 -->
# Conversation-scoped context cache — how does prepended context stay frozen for a session yet refresh on /clear and compaction?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** memoize-as-session-cache with explicit invalidation partners.

## getUserContext / getSystemContext
**Path/Symbol:** `src/context.ts:getUserContext` (:155-189), `getSystemContext` (:116-150), `setSystemPromptInjection` (:29-34); invalidation sites `src/commands/clear/caches.ts:52-54`, `src/services/compact/postCompactCleanup.ts:59`, compact re-announce `src/services/compact/compact.ts:567-578`.
**Signature:** both `memoize(async (): Promise<{[k: string]: string}>)`; lodash memoize keyed on zero args = one value per process.
**Data Shape:** userContext = `{ agentMd?, currentDate }`; systemContext = `{ gitStatus?, cacheBreaker? }`.

### Decisive source
```ts
// CLAUDE_CODE_DISABLE_AGENT_MDS (legacy: ...CLAUDE_MDS): hard off, always.
// --bare: skip auto-discovery (cwd walk), BUT honor explicit --add-dir.
// --bare means "skip what I didn't ask for", not "ignore what I asked for".
const shouldDisableAgentMd =
  isEnvTruthy(process.env.CLAUDE_CODE_DISABLE_AGENT_MDS ?? ...) ||
  (isBareMode() && getAdditionalDirectoriesForAgentMd().length === 0)
const agentMd = shouldDisableAgentMd ? null
  : getAgentMds(filterInjectedMemoryFiles(await getMemoryFiles()))
// Cache for the auto-mode classifier (yoloClassifier.ts reads this
// instead of importing agentmd.ts directly, which would create a
// cycle through permissions/filesystem → permissions → yoloClassifier).
setCachedAgentMdContent(agentMd || null)
```

**Flow:** first call per process computes and freezes (git status snapshot + AGENT.md walk + date line) → `/clear` clears all three caches (`getUserContext/getSystemContext/getGitStatus.cache.clear?.()`) → post-compact cleanup clears getUserContext so regenerated context reflects post-compact state ("the next turn hits the getUserContext cache and never reaches" the fresh computation otherwise) → optional BREAK_CACHE injection setter clears BOTH context caches on change.
**Invariant:** everything prepended to EVERY conversation must be conversation-stable, hence memoized; anything that changes mid-session belongs in tail attachments, never here; invalidation has exactly three legitimate triggers (clear, compact, explicit injection set) — no TTL, no mtime checks; bare-mode semantics are SUBTRACTIVE-not-absolute ("skip what I didn't ask for"); the classifier cache-break write is deliberate import-cycle surgery, keep it at this seam.
**Probe:** no upstream test (coverage caveat). Deterministic probe: `grep -rn "\.cache.clear" src/commands/clear/caches.ts src/services/compact/postCompactCleanup.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getUserContext getSystemContext memoize agentMd cache", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt memoize-as-conversation-cache with enumerated invalidation events; adapt what goes into each context map; omit legacy env aliases. Porting trap: recomputing prepended context per turn busts the prompt cache wholesale; forgetting the post-compact clear leaves stale AGENT.md/date in every subsequent turn's prefix.
