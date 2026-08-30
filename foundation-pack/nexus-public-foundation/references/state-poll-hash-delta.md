<!-- capsule-v2 -->
# State poll hash-delta protocol — how do you push UI state updates without a websocket and without re-sending unchanged values?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`StateComponent.java` 137L whole-file + `StateContributor.java`); Codebase Memory `nexus-public`. **Question:** The UI polls state every few seconds — what stops the server from shipping the full state document every time?

## Client sends {key: lastSeenHash}; server pre-seeds null for EVERY requested key, asks StateContributors, SHA1-hashes each value's JSON, returns StateValueXO ONLY when hash differs; absent contributors leave null (UI deletes the key)
**Path/Symbol:** `public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/internal/state/StateComponent.java` — boot-unique `serverId` with cluster `ignore.` prefix (:62-68), `@DirectPollMethod getState(hashes)` (:70-104), null pre-seed loop (:76-80), contributor iteration with per-contributor try/catch ignore (:82-99), `maybeSend` remove-then-compare (:106-126), Gson→SHA1 hashing (:128-143); SPI: `StateContributor.getState()` nullable map (`StateContributor.java` :24-31).
**Signature:** `public Map<String, Object> getState(final Map<String, String> hashes)` (Ext.Direct poll); SPI: `@Nullable Map<String, Object> getState()`.
**Data Shape:** request `{stateKey: sha1hex}`; response values are either `null` (unchanged-or-gone) or `StateValueXO{hash, value}`; keys requested but never contributed stay null ⇒ client-side removal. `serverId` = `System.nanoTime()` string, prefixed `ignore.` when clustered so UI event listeners skip reboot detection on other nodes.

### Decisive source
```java
// :76-80 — echo-null contract
for (String key : hashes.keySet()) {
  values.put(key, null);
}

// :109-120 — delta decision
values.remove(key);
String hash = hash(value);
if (!Objects.equal(hash, hashes.get(key))) {
  StateValueXO data = new StateValueXO();
  data.setHash(hash);
  data.setValue(value);
  values.put(key, data);
}
```

**Flow:** poll arrives → every requested key starts as null → each StateContributor runs inside its own catch-all (one broken contributor can't fail the poll; blank keys warn+skip) → for each produced key: hash the value's pretty-printed JSON with SHA1, compare to client's last-seen → changed ⇒ wrap {hash,value}, unchanged ⇒ stays null → `serverId` appended through same delta path → response. UI stores new hashes; nulls delete local state entries.
**Invariant:** (1) Null means "you already have it OR it no longer exists" — clients MUST treat null as removal candidate keyed by their own prior interest, which is why the pre-seed loop exists. (2) Hash is over SERIALIZED JSON (Gson), not object identity — contributors returning fresh objects each tick still dedupe correctly. (3) Contributor failure is isolated and logged at WARN, never propagated. (4) Clustered nodes prefix serverId with `ignore.` so reconnects to peer nodes don't trigger "server restarted" resets.
**Probe:** deterministic anchors: `grep -c 'maybeSend' public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/internal/state/StateComponent.java` = 3 (2 call sites + definition); `grep -c 'ignore\.' public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/internal/state/StateComponent.java` = 1 (:66 ternary — the literal appears once; both clustered and non-clustered boots flow through it). Direct test coverage: `RaptureWebResourceBundleTest` exercises the embedded-state path; dedicated StateComponentTest lives under `internal/state/` (BundleStateContributorTest sibling present).
**Retrieve:** search_graph project nexus-public query "StateComponent maybeSend DirectPollMethod" — resolves Methods :62-68/:70+ line-exact.
**Verdict:** Adopt hash-delta polling for any periodically-refreshed UI state over plain HTTP. Adapt hashing (SHA1-of-Gson is fine but any stable canonical serialization works). Omit Ext.Direct transport specifics.
