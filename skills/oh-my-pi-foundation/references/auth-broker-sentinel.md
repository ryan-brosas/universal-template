<!-- capsule-v2 -->
# Auth-broker snapshot & sentinel refresh tokens — how do credentials reach worker processes without leaking refresh tokens?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** What does the wire snapshot contain, how are remote rows refreshed, and why must sentinels never be treated as real tokens?

## Auth-broker snapshot & sentinel refresh tokens
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `REMOTE_REFRESH_SENTINEL = "__remote__"` (:336) + `exportSnapshot` (6567–6583) + `AuthCredentialSnapshot` (:354–362) + remote-store hooks on `AuthCredentialStore` (refreshOAuthCredential :478, prepareForRequest :490, getUsageReport :517 with "null is authoritative" contract :509–514).
**Signature:** `exportSnapshot(): {generation, generatedAt, credentials: [{id, provider, credential: SnapshotCredential, identityKey}]}`.
**Data Shape:** Snapshot = per-row redacted credential where OAuth `refresh` is REPLACED by the sentinel; served by broker `GET /v1/snapshot`. Remote store implements mutating ops as broker calls; local SQLite leaves optional hooks undefined.

### Decisive source
```ts
const redacted: SnapshotCredential =
	credential.type === "api_key" ? credential : { ...credential, refresh: REMOTE_REFRESH_SENTINEL };
...
// getUsageReport hook contract:
// Returning `null` is authoritative — AuthStorage does NOT fall back to
// the local fetch path. The store hook owns the decision, since falling
// back would re-introduce the per-IP rate-limit problem the broker exists to avoid.
```

**Flow:** workers hold a `RemoteAuthCredentialStore` (disk-cached snapshot ≤1h stale); `prepareForRequest` waits out imminent rotations and re-syncs the snapshot before a caller sees a stale access token; refresh routes through the broker (`POST`), which owns the real tokens; `#findStoredCredentialIdForUsageCredential` explicitly strips sentinels before matching (`comparing it would match the FIRST OAuth row regardless of account`, :3198–3200). Generation counter + `pollExternalChanges`/`acknowledgeLocalChanges` keep multi-process consumers notified; block reads/writes flow through broker seams (`listCredentialBlocks`/`upsertCredentialBlock`).
**Invariant:** Refresh token bytes NEVER leave the broker — every consumer-side code path must treat `"__remote__"` as "unknown", never as a comparable secret or truthy refresh-token presence check (`sessionPreferredCanRefreshOrUse` checks `.trim().length > 0 || not-expired`, so sentinel rows stay usable via expiry). Hook precedence everywhere: caller option > store hook > local implementation.
**Probe:** `packages/ai/test/auth-storage-broker-no-sentinel.test.ts` (sentinel non-matching); `remote-auth-store.test.ts`; `auth-storage-usage-cache.test.ts:394` (`serializes a persisted Codex refresh and returns an upgraded plan`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "REMOTE_REFRESH_SENTINEL exportSnapshot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot redaction + authoritative-null hook contracts + generation-based change polling; adapt transport (broker HTTP vs host RPC); omit the specific endpoint surface (`/v1/*`). A porter who compares sentinel refresh tokens for identity will cross-link unrelated accounts.
