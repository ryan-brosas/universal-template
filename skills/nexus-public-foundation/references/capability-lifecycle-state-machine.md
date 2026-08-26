<!-- capsule-v2 -->
# Capability reference state machine — how do you enforce a NEW→DISABLED→ENABLED→ACTIVE lifecycle so illegal transitions are impossible and callback failures never corrupt state?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-core/.../internal/capability/DefaultCapabilityReference.java`); Codebase Memory `nexus-public`. **Question:** How does a plugin/extension object carry enabled+active flags through create/load/update/remove without letting a failing lifecycle callback leave it half-transitioned?

## Per-reference State-pattern machine guarded by its own RW lock
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/capability/DefaultCapabilityReference.java` — `State` base (:420–480), `NewState` (:482–538), `DisabledState` (:540–619), `EnabledState` (:621–679), `ActiveState` (:681–720), `RemovedState` (:722–738); public mutators `enable/disable/activate/passivate/create/load/update/remove` (:164–342); failure latch `setFailure/resetFailure` (:393–418).
**Signature:** `private void update(Map properties, Map previousProperties, Map encryptedProperties, boolean force)`; each state method `void enable()`, `void activate()`, etc.
**Data Shape:** `stateLock = ReentrantReadWriteLock()` wraps every read (`isEnabled`, `isActive`, `failure`) and write. Two property maps are kept: `capabilityProperties` (decrypted view) and `encryptedProperties` (secret-ID view, returned by `properties()` :344–354). `failure` + `failingAction` latch the last callback exception.

### Decisive source
```java
// Base State: every operation ILLEGAL by default — subclasses opt IN
public void activate() {
  throw new IllegalStateException("State '" + toString() + "' does not permit 'activate' operation");
}

// EnabledState.activate: gate on condition, flip AFTER success
public void activate() {
  if (activationHandler.isConditionSatisfied()) {
    try {
      capability.onActivate();
      resetFailure();
      state = new ActiveState();                       // state flips only after onActivate succeeds
      eventManager.post(new CapabilityEvent.AfterActivated(capabilityRegistry, this));
    } catch (Exception e) { setFailure("Activate", e); }
  }
}

// ActiveState.passivate: flips BEFORE the callback (opposite order!)
public void passivate() {
  try {
    state = new EnabledState();
    eventManager.post(new CapabilityEvent.BeforePassivated(capabilityRegistry, this));
    capability.onPassivate();
  } catch (Exception e) { setFailure("Passivate", e); }
}
```

**Flow:** constructor sets `state = new NewState()` and calls `capability.init(context,…)` → `create()/load()` (only legal in NewState) populate both maps, post `Created`, call `onCreate()`/`onLoad()`, bind validity handler, land in DisabledState — the `finally` guarantees DisabledState even if the callback threw (failure is latched, not propagated) → `enable()` (only Disabled) swaps to EnabledState then binds activation handler → `activate()` (only Enabled, only when activation condition satisfied) calls `onActivate()` and flips to ActiveState on success → `passivate()` (only Active) flips to EnabledState first, then `onPassivate()` → `remove()` (from Disabled) disables, releases validity handler, `onRemove()`, lands in RemovedState via `finally`.
**Invariant:** (1) every transition is total — an operation not permitted by the current state throws `IllegalStateException` naming the state, it is never silently ignored except the documented idempotent no-ops (`disable` when disabled, `passivate` when not active, `activate` when active). (2) A callback exception NEVER propagates and NEVER blocks the transition: it is latched via `setFailure(action, e)` which posts `CallbackFailure`; next successful op posts `CallbackFailureCleared`. (3) Asymmetric flip order: activation flips state AFTER the callback succeeds (a failed activate leaves you ENABLED with a failure latch — pinned by `activateProblem`), passivation flips BEFORE (a failed passivate still deactivates — pinned by `passivateProblem`). (4) `update` skips `onUpdate()` entirely when properties are unchanged unless `force` (`sameProperties` :383–391, null-asymmetric equality).
**Probe:** `nexus-core/src/test/java/org/sonatype/nexus/internal/capability/DefaultCapabilityReferenceTest.java` — `activateProblem` (:233–251: failure ⇒ stays enabled, `hasFailure()==true`, later `passivate()` is a no-op), `passivateProblem` (:254–271: deactivated anyway + failure latched), `updateProblemWhenActive` (:294–313: failed update passivates an active capability), `updateIsNotForwardedToCapabilityIfSameProperties` (:359), `activateWhenActive` (:189: second activate never re-calls `onActivate`).
Coverage caveat: tests mock the capability + handlers; the condition-gate interplay itself is exercised only indirectly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "DefaultCapabilityReference NewState EnabledState ActiveState setFailure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the throw-by-default State hierarchy, the RW-locked mutator shell, the failure latch with cleared events, and the asymmetric flip ordering (flip-after-success on activate, flip-before-callback on passivate). Adapt the specific event classes and the encrypted/decrypted dual-map to your secrets model. Omit the Guava/Spring wiring and the `capabilityAs(Class)` unchecked cast helper.
