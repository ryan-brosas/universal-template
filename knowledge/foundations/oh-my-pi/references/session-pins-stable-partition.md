<!-- capsule-v2 -->
# Session pinning — how do pinned sessions sort to the top of every resume surface without breaking recency order or surviving stale ids?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the persistence shape and stable-partition contract for session pins, and why key them by id rather than path?

## Session pins stable partition
**Path/Symbol:** `packages/coding-agent/src/session/session-pins.ts:` `loadPinnedSessionIds` (:13–23), `toggleSessionPin` (:26–31), `sortPinnedFirst` (:38–44); consumers `session-manager.ts:2928,2934`, `modes/controllers/selector-controller.ts:1586`.
**Signature:** `loadPinnedSessionIds(agentDir?: string): Promise<Set<string>>; toggleSessionPin(sessionId: string, agentDir?: string): Promise<boolean>; sortPinnedFirst(sessions: SessionInfo[], pinnedIds: ReadonlySet<string>): SessionInfo[]`.
**Data Shape:** `~/.omp/session-pins.json` = JSON array of session-id strings (pretty-printed with tabs); toggle = load-modify-write of the whole set.

### Decisive source
```ts
// Stable partition putting pinned sessions on top: within each group the
// caller's order (recency) is preserved. Unknown ids are a no-op so stale
// pins for deleted sessions never disturb the listing.
export function sortPinnedFirst(sessions: SessionInfo[], pinnedIds: ReadonlySet<string>): SessionInfo[] {
	if (pinnedIds.size === 0) return sessions;
	const top: SessionInfo[] = [];
	const rest: SessionInfo[] = [];
	for (const session of sessions) (pinnedIds.has(session.id) ? top : rest).push(session);
	return top.length > 0 ? [...top, ...rest] : sessions;
}
```

**Flow:** toggle → `loadPinnedSessionIds` → delete returns true ⇒ it WAS pinned ⇒ unpin; else add → persist `[...pinned]` → report new state. Listing surfaces call `loadPinnedSessionIds()` then wrap their ordered list with `sortPinnedFirst`.
**Invariant:** Pins are keyed by session ID, not file path, so `/move` renames keep the pin. Corruption degrades to an empty set WITH a warning — never break the resume picker over a bad pins file; non-string array entries are filtered out rather than rejected. The partition is STABLE: within each group caller order (recency) survives untouched, and `top.length === 0` returns the ORIGINAL array reference (not a copy) so a no-pin set costs nothing.
**Probe:** `test/slash-commands/pin.test.ts` pins the slash-command legs (`"toggles pin for the active session when invoked without arguments"` :65, `"pins a specific session by id or prefix"` :93); module invariants verified byte-exact at pin: `grep -cF 'pinnedIds.size === 0' src/session/session-pins.ts` → 1 (executed green).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "loadPinnedSessionIds sortPinnedFirst pinned sessions", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `sortPinnedFirst session-pins.ts:38-44`, `loadPinnedSessionIds :13-23`.

## Verdict
Adopt the id-keyed pins file, degrade-to-empty corruption handling, and stable partition. Adapt storage location/agentDir resolution to your host. Omit nothing — this module's value is precisely its smallness plus the three invariants.
