<!-- capsule-v2 -->
# Session store over model layer — how does express-session persist without a session table driver?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What must a custom express-session Store implement when sessions live in an app-model row?

## SessionStore
**Path/Symbol:** `ghost/core/core/server/services/auth/session/session-store.js:SessionStore` (:3–43); wiring `express-session.js` (:1–48).
**Signature:** `class SessionStore extends Store` implementing `destroy(sid, cb)`, `get(sid, cb)`, `set(sid, sessionData, cb)`, `clear(cb)` via injected SessionModel.
**Data Shape:** rows keyed by `session_id`; opaque `session_data` blob (JSON of the session object incl. verified flags); upsert semantics on set.
### Decisive source
```js
get(sid, callback) {
  this.SessionModel.findOne({ session_id: sid }).then((model) => {
    if (!model) { return callback(null, null); }
    callback(null, model.get('session_data'));
  }).catch(callback);
}
set(sid, sessionData, callback) {
  this.SessionModel.upsert({ session_data: sessionData }, { session_id: sid }).then(() => callback(null)).catch(callback);
}
```
**Flow:** express-session middleware calls get on every request → store returns the RAW session_data blob (deserialization handled by the library) → set upserts after each mutation (verified flag flips, auth-code rotations) → destroy on logout/regenerate.
**Invariant:** Callback-style contract with promise plumbing — errors MUST go to `callback(err)` or the middleware hangs. Missing row ⇒ `callback(null, null)` NOT an error (distinguishes logged-out from store failure). All verification state rides inside the opaque blob, which is why regenerate-then-copy (carry-over capsule) is required for rotation.
**Probe:** `grep -cF "upsert({ session_data: sessionData }, { session_id: sid })" ghost/core/core/server/services/auth/session/session-store.js` → expect `1`; direct tests: `ghost/core/test/unit/api/canary/session.test.js` controller suite + e2e `ghost/core/test/e2e-api/admin/session-invalidation.test.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "SessionStore express-session", limit: 5, fields: ["signature", "name", "file"] });
```
**Drift note:** class nodes index under their file; query `createSessionForUser` also surfaces this file's neighbors.

## Verdict
Adopt Store-subclass shape with null-not-error misses and upsert writes. Adapt persistence to host DB; keep callback error routing exact.
