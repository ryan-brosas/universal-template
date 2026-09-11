<!-- capsule-v2 -->
# Activation condition composition — how do you gate a plugin's activation on its own condition AND global health, and what happens when the capability's condition is null or blows up?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-core/.../internal/capability/ActivationConditionHandler.java`); Codebase Memory `nexus-public`. **Question:** How do you combine a per-capability activation condition with system-wide preconditions so one failing capability never activates — without hard-coding the preconditions into each capability?

## Handler composes (capability-condition ∧ nexus-active ∧ no-failures ∧ no-duplicates) on bind
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/capability/ActivationConditionHandler.java` — `bind()` (:76–103), `release()` (:105–112), `handle(Satisfied/Unsatisfied)` (:60–74), `isConditionSatisfied()` (:56–58), `explainWhyNotSatisfied()` (:121–123).
**Signature:** `ActivationConditionHandler bind()`; `@Subscribe public void handle(ConditionEvent.Satisfied event)` (`@AllowConcurrentEvents`).
**Data Shape:** single field `Condition activationCondition` — null until first `bind()`, reset to null by `release()`. The composed condition is a Conjunction of 4 leaves; identity-compared (`==`) against event sources.

### Decisive source
```java
activationCondition = conditions.logical()
    .and(
        capabilityActivationCondition,                    // capability's own, may be null
        conditions.nexus().active(),                      // app is past its lifecycle gate
        conditions.capabilities().capabilityHasNoFailures(),  // this capability not failure-latched
        conditions.capabilities().capabilityHasNoDuplicates()); // config not duplicated elsewhere
if (activationCondition instanceof CapabilityContextAware) {
  ((CapabilityContextAware) activationCondition).setContext(reference.context());
}
...
catch (Exception e) {
  activationCondition = conditions.never("Failed to determine activation condition"); // FAIL-CLOSED
}
```
```java
// event-driven activation: satisfied ⇒ activate, unsatisfied ⇒ passivate (both no-op in wrong states)
public void handle(final ConditionEvent.Satisfied event) {
  if (event.getCondition() == activationCondition) { reference.activate(); }
}
```

**Flow:** `bind()` (called from DisabledState.enable / NewState.create|load finally): if already bound, no-op → fetch the capability's `activationCondition()`; **null becomes `conditions.always(...)`** → wrap in the 4-way AND → propagate `CapabilityContext` to context-aware leaves → `bind()` the composite then register as an event listener → later ConditionEvents re-activate/passivate automatically; `release()` unregisters and releases the composite.
**Invariant:** (1) A capability NEVER supplies its own "app is ready" check — the handler always ANDs it in; a capability returning `null` opts into "always" rather than bypassing gates. (2) Exception while obtaining the capability's condition ⇒ `never()` + error log: a broken condition can only PREVENT activation, never cause it (fail-closed). (3) Handlers compare event source by reference identity, so unrelated conditions sharing an event bus cannot trigger activation. (4) `isSatisfied()` short-circuits to false when unbound (`activationCondition != null && …`). (5) State descriptions surface `explainWhyNotSatisfied()` for UI diagnosis instead of a boolean.
**Probe:** `DefaultCapabilityReferenceTest.java` — `enableWhenNotEnabled` (:153–161 verifies `activationCondition.bind()` on enable), `disableWhenEnabled` (:164–176 verifies `release()` on disable); the AND-composition itself is exercised via the mocked `ConjunctionCondition` in setUp (:94–151).
Coverage caveat: the real `ConjunctionCondition` re-evaluation path is covered only indirectly through mocks here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "ActivationConditionHandler bind conditions logical and capabilityHasNoFailures", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bind-time composition with mandatory system-health leaves plus the null⇒always / exception⇒never fallback ladder, and identity-based event filtering. Adapt which global conditions you require (nexus-active/no-failures/no-duplicates are Nexus-specific). Omit the Guava EventBus specifics.
