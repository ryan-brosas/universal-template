<!-- capsule-v2 -->
# Signup-permit assistant state relay — how does a pre-signup AI prompt survive authentication to open a welcome doc?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Why store the prompt in a Permit instead of a cookie, and what is the exact write→read lifecycle?

## Prompt stored as AssistantStatePermit (1h TTL); cookie carries only the ID; getAndRemove consumes on first read and verifies docId
**Path/Symbol:** `app/server/lib/AssistantStatePermit.ts`: interface `{prompt, docId?}` (:23–26), `getAndRemoveAssistantStatePermit` (:36–45), `setAssistantStatePermit` (:56–64, TTL 1000*60*60 :60); consumer `ActiveDoc.getAssistantState` (`app/server/lib/ActiveDoc.ts` :2447–2455).
**Signature:** `getAndRemove(store, id): Promise<AssistantStatePermit|null>`; `set(store, permit): Promise<string>` (returns id).
**Data Shape:** Permits = server-side store keyed by id with TTL; cookies stay <4KB by carrying ids only.

### Decisive source
```ts
// set: prefix stripped from returned id
const key = await store.setPermit(permit, 1000 * 60 * 60);   // 1 hour
const id = key.replace(prefix, "");
// get-and-remove: consume-on-read
const permit = await store.getPermit(key);
await store.removePermit(key);
return permit;
// ActiveDoc.getAssistantState — docId binding check
const permit = await getAndRemoveAssistantStatePermit(store, id);
if (!permit || permit.docId !== this._docName) return null;
return pick(permit, "prompt");
```

**Flow:** `/api/assistant/start` stores `{prompt}` pre-auth → signup redirect sets a state COOKIE containing the permit ID → after signup, first doc creation rewrites the permit with its `docId` → opening that doc with `?assistantState=<id>` consumes the permit (deleted on read) and returns the prompt ONLY if the permit's docId matches THIS document.
**Invariant:** Consume-on-read makes replay impossible — a captured URL works at most once. The docId equality check prevents cross-document injection (permit minted for doc A can't seed chat in doc B); mismatch ALSO consumed it already (fail-closed: the id burns either way). Cookie-size constraint is the design driver — prompts are unbounded text, permits aren't. 1h TTL bounds orphaned permits.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "await store.removePermit(key)" app/server/lib/AssistantStatePermit.ts && grep -n "permit.docId !== this._docName" app/server/lib/ActiveDoc.ts'` → :43 consume; :2452 docId gate.
Direct tests: no dedicated spec file; exercised through signup-flow server suites — stated coverage caveat (grep-only anchors above).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"AssistantStatePermit getAndRemoveAssistantStatePermit permit signup","limit":5,"detail":"ids"}'
```

## Verdict
Adopt id-in-cookie/consume-on-read/docId-binding trio wholesale (auth-adjacent behavior); adapt store backend; omit nothing — each property closes a distinct replay/injection hole.
