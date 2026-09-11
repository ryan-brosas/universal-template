<!-- capsule-v2 -->
# Validity condition auto-remove — how do you make an extension self-destruct when its validity condition breaks, and why does a broken validity check REMOVE it instead of disabling?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-core/.../internal/capability/ValidityConditionHandler.java`); Codebase Memory `nexus-public`. **Question:** How do you implement "this capability exists only while X holds" — including the two-phase bind (wait for app-active, then watch validity) — and which failure direction does each fallback take?

## Two-phase handler: nexus-active gates validity watching; validity-unsatisfied ⇒ disable + registry.remove
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/capability/ValidityConditionHandler.java` — `bind()` (:88–98), `release()` (:100–107), Satisfied/Unsatisfied handlers (:63–86), `bindValidity()/releaseValidity()` (:109–138).
**Signature:** `ValidityConditionHandler bind()`; `private void handle(ConditionEvent.Unsatisfied event)` branches on which condition fired.
**Data Shape:** two nullable conditions: `nexusActiveCondition` (phase gate) and `validityCondition` (lazily bound only while app is active). Handler registered on the event bus once per phase-1 bind.

### Decisive source
```java
// phase 2 arming: when the app becomes active, start watching validity
public void handle(final ConditionEvent.Satisfied event) {
  if (event.getCondition() == nexusActiveCondition) { bindValidity(); }
}

// validity broken ⇒ SELF-REMOVE (not just disable!)
public void handle(final ConditionEvent.Unsatisfied event) {
  if (event.getCondition() == nexusActiveCondition) { releaseValidity(); }
  else if (event.getCondition() == validityCondition) {
    reference.disable();
    try { capabilityRegistry.remove(reference.context().id()); }
    catch (Exception e) { log.error("Failed to remove capability with id '{}'", ...); }
  }
}

// phase-1 bind replays current state synchronously (no missed-event race)
nexusActiveCondition.bind();
eventManager.register(this);
if (nexusActiveCondition.isSatisfied()) {
  handle(new ConditionEvent.Satisfied(nexusActiveCondition));   // manual replay
}

catch (Exception e) {
  validityCondition = conditions.always("Always satisfied (failed to determine validity condition)"); // FAIL-OPEN
}
```

**Flow:** create/load finally calls `bind()` → phase 1: bind `nexus().active()`, register listener, synchronously replay its current satisfaction → when app becomes active (`Satisfied`), phase 2 `bindValidity()`: fetch `capability.validityCondition()`; exception ⇒ `always()` fail-open; null ⇒ `always()`; context-aware leaves get the context → any later `Unsatisfied` from THAT validity condition disables the reference and removes it from the registry (removal failure only logs — the reference is already disabled); app deactivating (`Unsatisfied` on nexusActive) releases the validity condition but keeps the handler armed.
**Invariant:** (1) The mirror-image of ActivationConditionHandler's policy: obtaining a VALIDITY condition fails OPEN (`always` = keep the capability), while obtaining an ACTIVATION condition fails CLOSED (`never`) — activation is additive risk, validity loss destroys config. (2) Validity breach deletes persisted state via registry.remove — this is intentional data destruction, so the removal path swallows exceptions after disable to guarantee the disable stands. (3) The synchronous replay in `bind()` closes the "already satisfied before I registered" race. (4) Release order on shutdown mirrors bind (replay Unsatisfied → unregister → release).
**Probe:** no dedicated direct test class for ValidityConditionHandler (coverage caveat — behavior verified by whole-file source read at the pinned commit; the remove path it calls into is pinned by DefaultCapabilityRegistryTest). Recorded honestly rather than invented.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "ValidityConditionHandler bindValidity releaseValidity nexusActiveCondition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase gating (don't watch volatile conditions before the host is up), the synchronous-replay bind, and the disable-then-remove ladder with swallowed removal errors. Adapt what "app active" means for your host. Omit the Nexus condition vocabulary; note that if you port this, decide explicitly whether YOUR validity breach should delete persisted state (Nexus says yes for capabilities of this kind).
