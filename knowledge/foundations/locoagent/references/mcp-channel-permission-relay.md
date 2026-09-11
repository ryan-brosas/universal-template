<!-- capsule-v2 -->
# Channel permission relay — how do approval prompts reach a phone over Telegram/iMessage/Discord without letting text replies self-approve?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How are human-readable approval codes generated (collision, keyboard, obscenity constraints) and how do structured events — never raw chat text — resolve a pending prompt?

## FNV-1a 5-letter IDs + delete-before-call resolution + dual-capability server opt-in
**Path/Symbol:** `src/services/mcp/channelPermissions.ts`: `PERMISSION_REPLY_RE` (:75), ID_ALPHABET minus 'l' (:77-78), blocklist + salt-rehash `shortRequestId` (:85-152), FNV-1a `hashToId` (:112-128), `truncateForPreview` 200 chars (:160-167), three-condition filter `filterPermissionRelayClients` (:177-194), callbacks factory (:209-240), gate `isChannelPermissionRelayEnabled` separate GrowthBook flag (:36-38).
**Signature:** `shortRequestId(toolUseID: string): string`; `createChannelPermissionCallbacks(): {onResponse(requestId, handler): unsub, resolve(requestId, behavior, fromServer): boolean}`.
**Data Shape:** alphabet `abcdefghijkmnopqrstuvwxyz` (a-z minus l; looks like 1/I); 25^5 ≈ 9.8M space, birthday collision needs ~3K simultaneous prompts; ~13,877 blocked IDs ≈ 1-in-700 hit rate, ≤10 salt retries.

### Decisive source
```ts
resolve(requestId, behavior, fromServer) {
  const key = requestId.toLowerCase()
  const resolver = pending.get(key)
  if (!resolver) return false
  // Delete BEFORE calling — if resolver throws or re-enters, the
  // entry is already gone. Also handles duplicate events (second
  // emission falls through — server bug or network dup, ignore).
  pending.delete(key)
  resolver({ behavior, fromServer })
  return true
}
// Inbound is a structured event: the server parses the user's "yes tbxkq"
// reply and emits notifications/claude/channel/permission with
// {request_id, behavior}. CC never sees the reply as text — approval
// requires the server to deliberately emit that specific event... (:7-13)
// filter: connected AND in --channels allowlist AND declares BOTH
// capabilities.experimental['claude/channel'] and ['claude/channel/permission'] (:169-176)
```

**Flow:** permission dialog fires → CC sends prompt + shortRequestId + truncated input preview to every qualifying channel server → human replies `yes tbxkq` → SERVER parses (regex exported for plugins) and emits the structured notification → CC's handler calls resolve() → first claimer wins; trust-boundary rationale documented in-file: the allowlist (tengu_harbor_ledger) is the boundary, not the terminal — a compromised channel could fabricate approvals, but it already has unlimited conversation-injection turns, so inject-then-self-approve is faster, not more capable (:15-23).
**Invariant:** Text in the general channel can NEVER approve anything (no regex on CC side); onResponse lowercases keys defensively so a future mixed-case caller can't silently never-match (:216-221); letters-only IDs keep phones from switching keyboard modes.
**Probe:** `grep -n 'ID_ALPHABET =' src/services/mcp/channelPermissions.ts` (`78:`) and `grep -n 'PERMISSION_REPLY_RE = ' src/services/mcp/channelPermissions.ts` (`75:`) and `grep -c 'pending.delete(key)' src/services/mcp/channelPermissions.ts` (`2` — unsubscribe :224 + delete-before-call :235) and `grep -n \"capabilities?.experimental?.\\['claude/channel/permission'\\]\" src/services/mcp/channelPermissions.ts` (`192:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "shortRequestId", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "filterPermissionRelayClients", limit: 5 });
```

## Verdict
Adopt structured-event-only resolution, delete-before-call map discipline, pronounceable-ID generation with blocklist rehash. Adapt reply grammar and channel set. Omit product telemetry.
