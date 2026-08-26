<!-- capsule-v2 -->
# Agents cache TTL + mtime sync bridge — how does in-process state learn what sibling processes wrote?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How do two processes sharing one registry keep each other's writes visible cheaply?

## Two caches with different invalidation disciplines
**Path/Symbol:** `store/agents.ts:getActiveAgents` (:115-186) + `AGENTS_CACHE_TTL_MS = 1000` (:61); `store/agents.ts:syncChannelStateFromDisk` (:19-52) with module-level `regMtimeCache` (:17).
**Signature:** `getActiveAgents(state, dirs): AgentRegistration[]`; `syncChannelStateFromDisk(state, dirs): boolean`.
**Data Shape:** `AgentsCache = { allAgents, filtered: Map<cacheKey, AgentRegistration[]>, timestamp, registryPath }`; per-cwd filtered lists keyed `${excludeName}:${myCwd}` when scopeToFolder.

### Decisive source
```ts
const stat = fs.statSync(regPath);
const lastMtime = regMtimeCache.get(regPath) ?? 0;
// Skip the read if the file hasn't been modified since last sync.
if (stat.mtimeMs <= lastMtime) return false;
regMtimeCache.set(regPath, stat.mtimeMs);
```
vs the peers cache:
```ts
if (agentsCache && agentsCache.registryPath === dirs.registry &&
    now - agentsCache.timestamp < AGENTS_CACHE_TTL_MS) {
  const cachedFiltered = agentsCache.filtered.get(cacheKey);
  if (cachedFiltered) return cachedFiltered;   // memoized per filter key
```

**Flow:** own-channel state uses stat-gated re-read (mtime strictly greater ⇒ parse + diff + adopt); peer listings use a 1s TTL cache whose miss path re-scans the whole registry dir, prunes dead pids by unlinking them, then memoizes each filter key inside the SAME TTL window.
**Invariant:** Two DIFFERENT freshness models: self state = event-driven mtime gate (CLI writes must surface promptly, no polling cost), peers = coarse TTL (staleness ≤1s acceptable). `invalidateAgentsCache()` is called after every local mutation so OWN writes are visible immediately while siblings' arrive within the TTL. `<=` in the mtime guard makes equal-timestamp rewrites invisible (idempotent no-op).
**Probe:** direct tests `tests/swarm/project-isolation.test.ts::should filter agents by cwd when scopeToFolder is true`, `tests/channel.test.ts::avoids collisions...`; `grep -n "AGENTS_CACHE_TTL_MS = 1000" store/agents.ts` (=1 hit at :61); `grep -c "stat.mtimeMs <= lastMtime" store/agents.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "syncChannelStateFromDisk getActiveAgents invalidateAgentsCache", limit: 5 });
```

## Verdict
Adopt the dual-cache split (mtime-gate for shared single-agent files, short TTL + per-filter memoization for directory scans); adapt TTL values; omit cwd-filter key composition if you don't scope agents per folder.
