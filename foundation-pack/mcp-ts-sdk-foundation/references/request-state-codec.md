<!-- capsule-v2 -->
# RequestState HMAC codec — how do you let attacker-controlled state round-trip through the client without hand-rolling crypto?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A multi-round-trip flow mints a `requestState` the client echoes back on retry — what integrity/binding/expiry envelope makes that safe?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/requestStateCodec.ts`: `createRequestStateCodec` (:145-267) incl. key-snapshot TOCTOU comment, `constantTimeTagEqual` (:110-121), wire-shape docblock (:120-144).
**Signature:** `createRequestStateCodec<T>(options: {key: Uint8Array|string; ttlSeconds?=600; bind?: (ctx)=>string}): { mint(payload:T, ctx?): Promise<string>; verify(state, ctx): Promise<T> }`.
**Data Shape:** Wire = `"v1." + base64url(JSON{p:payload, exp, b?}) + "." + base64url(HMAC(PREFIX+body))`. Key MUST be ≥32 bytes (RangeError otherwise); non-finite ttlSeconds rejected at construction (Infinity/NaN would serialize `exp` as JSON null ⇒ misleading 'expired' on every round-trip).

### Decisive source
```ts
// Snapshot the key bytes at construction. Holding the caller's reference would
// let a post-construction mutation (e.g. zeroing the secret for hygiene)
// silently change the key the lazy importedKey() reads on first mint/verify —
// a TOCTOU on the secret.
const keyBytes = typeof options.key === 'string' ? new TextEncoder().encode(options.key) : Uint8Array.from(options.key);
// The MAC covers `PREFIX + body` so the version tag is bound: a valid body.mac
// pair under `v1.` cannot be transplanted to a future `v2.` codec under the same key.
const mac = await subtle.sign('HMAC', await importedKey(), utf8.encode(PREFIX + body));
```

**Flow:** verify order: shape (`v1.` prefix + last-dot split) → MAC FIRST (every other reason reachable only for values we minted) → JSON decode fail-closed → expiry → bind-tag compare via fixed-length XOR accumulator (SubtleCrypto.verify is constant-time for the body MAC). Bind tags are domain-separated (`'mcp.requestState.bind:'` label), truncated to 128 bits, and store only the HMAC tag of e.g. `${method}\0${clientId}` — never the raw principal.

**Invariant:** Opaque fixed reason codes only ('malformed'/'mac'/'expired'/'bind') — never interpolate expected/actual binding values (principal identifiers). Fail-closed on CONFIG DRIFT: a token minted with a bind callback is REJECTED by an instance without one (accepting would silently drop the principal-binding guarantee). The lazy CryptoKey import reads only the owned snapshot.

**Probe:** `packages/server/test/server/requestStateCodec.test.ts` :29 ("rejects a tampered body with reason \"mac\""), :79 ("bind mismatch — message is opaque"), :112 ("rejects a bound token when bind is unconfigured (fail-closed on config drift)"), :123 ("snapshots a Uint8Array key at construction"), :137 ("version prefix is bound into the MAC").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "createRequestStateCodec constantTimeTagEqual bindTag", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt MAC-first verify order + version-bound MAC + tag-only binding + construction-time key snapshot for any round-tripping state token; adapt reason codes/labels; omit WebCrypto runtime shims if Node-only.
