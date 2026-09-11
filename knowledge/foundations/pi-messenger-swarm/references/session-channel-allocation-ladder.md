<!-- capsule-v2 -->
# Session-channel allocation ladder — how does a resumed session get the SAME phrase channel while a fresh one gets a unique one?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How are human-friendly channel names allocated collision-free and made stable across process restarts?

## Memorable-name generate → kebab → collision suffix ladder
**Path/Symbol:** `channel.ts:generateSessionChannelId` (:362-365), `channel.ts:allocateSessionChannelId` (:349-360), `channel.ts:ensureSessionChannel` (:389-399), `lib/names.ts:generateMemorableName` (:174-206).
**Signature:** `allocateSessionChannelId(dirs: Dirs, baseId: string): string`; `createSessionChannel(dirs, sessionId?, createdBy?)`.
**Data Shape:** base id = kebab-cased adjective+noun from themed word lists (default/nature/space/minimal/custom). Collision suffixes `-2..-99`, then a random base36 tail.

### Decisive source
```ts
function allocateSessionChannelId(dirs: Dirs, baseId: string): string {
  const normalizedBase = normalizeChannelId(baseId);
  if (!getChannel(dirs, normalizedBase)) return normalizedBase;
  for (let i = 2; i <= 99; i++) {
    const candidate = `${normalizedBase}-${i}`;
    if (!getChannel(dirs, candidate)) return candidate;
  }
  const suffix = Math.random().toString(36).slice(2, 6);
  return `${normalizedBase}-${suffix}`;
}
```

**Flow:** `ensureSessionChannel` FIRST looks up any existing channel whose header `sessionId === sessionId` (`findChannelBySessionId`) and returns it unchanged — resume-stability comes from that lookup, NOT from name determinism; only on miss does it mint a fresh memorable name and run the allocation ladder.
**Invariant:** Name uniqueness is checked against DISK (getChannel), not an in-memory set, because sibling processes create channels concurrently; the random-suffix fallback exists because `-2..-99` can theoretically exhaust. Porters who make names deterministic-per-session instead break two sessions sharing a project.
**Probe:** direct tests `tests/channel.test.ts::creates phrase-based session channels and restores them for the same pi session id` (regex `/^[a-z0-9]+(?:-[a-z0-9]+)+$/`, restore-by-sessionId) and `::avoids collisions when two session channels would get the same phrase`; `grep -c "i <= 99" channel.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "allocateSessionChannelId ensureSessionChannel findChannelBySessionId", limit: 5 });
```

## Verdict
Adopt lookup-by-owner-id-before-minting as THE resume mechanism plus bounded numeric suffix ladder with random escape hatch; adapt word lists/themes freely (pure data); omit the `session-` prefix special-case in `normalizeChannelRecord` type inference unless you also carry legacy ids.
