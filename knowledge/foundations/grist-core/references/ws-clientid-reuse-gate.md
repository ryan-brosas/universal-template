<!-- capsule-v2 -->
# ws-clientid-reuse-gate — When may a reconnecting websocket take over an existing Client object, and what does refusal cost?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** A tab presents a known clientId — under what conditions is the lingering Client reused vs replaced?

## canAcceptConnection three-clause gate
**Path/Symbol:** `app/server/lib/Client.ts:canAcceptConnection` (:317–329); called from `Comm._onWebSocketConnection` :243–249.
**Signature:** `public canAcceptConnection(authSession: AuthSession): boolean` returning `!this._websocket && this._authSession.userId === authSession.userId && !this._authSession.credential && !authSession.credential`.
**Data Shape:** three clauses: (1) no live socket on the Client (`!this._websocket`), (2) same userId, (3) NEITHER session carries a credential.

### Decisive source
```ts
// Refuse if another websocket is currently active. It may be a new browser tab
// (which may reuse clientId from a copy of sessinStorage). It will need its own
// Client object.
//
// Also refuse if the reconnecting user differs from this Client's, for stronger
// security, so that we don't treat a clientId on its own as a secret sufficient
// to impersonate a user.
return !this._websocket && this._authSession.userId === authSession.userId &&
  !this._authSession.credential && !authSession.credential;
```

**Flow:** reconnect presents clientId → Comm resolves identity FIRST → canAcceptConnection decides: any clause fails ⇒ brand-new Client object with a fresh random clientId; the old Client stays intact and independent (its own destroy timer / reload flows) → all pass ⇒ SAME Client survives: doc sessions and undo/redo history continuity carry across reloads, missed-message ledger persists for resume.
**Invariant:** clientId is NOT a bearer secret — an anonymous reconnect guessing a valid id gets its own fresh anonymous Client while the real user's Client remains untouched (pinned by test). Credential-bearing sessions are excluded from reuse ENTIRELY because userId alone cannot distinguish two token sessions; the source names the relaxation path (compare credential compatibility). Refusal cost is small BY DESIGN: new Client ⇒ needReload ⇒ docs reopen fresh.
**Probe:** `test/server/Comm.ts:1233` ("should not let a different identity reuse a clientId on reconnect" — anon guess yields new clientId + needReload:true while chimpy's Client keeps his identity) and :1259 ("should let the same identity reuse a clientId on reconnect").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "canAcceptConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-clause gate verbatim — the credential-exclusion clause is the security-critical one porters drop first. Adapt what counts as a credential (Grist: API keys/OAuth tokens vs cookie sessions). Omit sessionStorage clientId persistence details (browser-side).
