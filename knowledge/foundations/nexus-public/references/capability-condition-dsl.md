<!-- capsule-v2 -->
# Reactive condition DSL — how do you build composable boolean conditions that push Satisfied/Unsatisfied events instead of being polled, and stay correct under re-entrancy?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-capability/.../condition/ConditionSupport.java` + `internal/CompositeConditionSupport.java`); Codebase Memory `nexus-public`. **Question:** How do you implement AND/OR/NOT over event-driven predicates so a composite re-evaluates only when a watched leaf changes, and binding is idempotent?

## bind/release idempotence + edge-triggered setSatisfied + identity-filtered re-composition
**Path/Symbol:** `public/common/components/nexus-capability/src/main/java/org/sonatype/nexus/capability/condition/ConditionSupport.java` — `isSatisfied` (:70), `bind()` (:79–85), `release()` (:88–94), `setSatisfied(boolean)` (:121–133); `.../condition/internal/CompositeConditionSupport.java` — `doBind` (:58–65), `doRelease` (:67–72), `handle(Satisfied|Unsatisfied)` (:76–89), `reevaluate` abstract (:111), `shouldReevaluateFor` (:117–122); `LogicalConditions.and/or/not` (:27–47); leaf exemplars `CapabilityHasNoFailuresCondition.doBind/handle` (:57–87), `CapabilityOfTypeExistsCondition.doBind` (:63–67 synchronous replay).
**Signature:** `protected abstract void doBind(); protected abstract void doRelease(); protected void setSatisfied(final boolean satisfied)`; `Condition and(Condition... conditions)`.
**Data Shape:** two booleans per condition: `satisfied` (the value) and `active` (bound or not). Composites hold `Condition[]` (≥2 for and/or, exactly 1 for not). Events: `ConditionEvent.Satisfied/Unsatisfied(condition)`.

### Decisive source
```java
@Override
public final Condition bind() {          // final = idempotence is NOT subclass-overridable
  if (!active) { active = true; doBind(); }
  return this;
}

protected void setSatisfied(final boolean satisfied) {
  if (this.satisfied != satisfied) {     // EDGE-TRIGGERED: only on real change
    this.satisfied = satisfied;
    if (active) {
      getEventManager().post(this.satisfied ? new ConditionEvent.Satisfied(this)
                                            : new ConditionEvent.Unsatisfied(this));
    }
  }
}
```
```java
// Composite: register FIRST, then seed — leaves replay their current state on doBind
protected void doBind() {
  for (final Condition condition : conditions) { condition.bind(); }
  getEventManager().register(this);
  setSatisfied(reevaluate(conditions));
}

private boolean shouldReevaluateFor(final Condition condition) {
  for (final Condition watched : conditions) { if (watched == condition) return true; }  // identity filter
  return false;
}
```

**Flow:** leaf `doBind()` registers its own listeners AND synchronously seeds itself from current world state (`CapabilityOfTypeExistsCondition.doBind` replays `new CapabilityEvent.Created(...)` per existing reference when the registry already has matches) → composite binds children first, registers, then evaluates once → any child edge triggers composite re-evaluation whose own `setSatisfied` is again edge-triggered, so state changes propagate up the tree as events, one per real transition.
**Invariant:** (1) `bind()`/`release()` are final + flag-guarded: double-binding must never double-register bus listeners. (2) Events are edge-triggered — a condition that re-posts its unchanged state would loop the tree forever. (3) Composite seeding order (children bind → self-register → evaluate) closes the missed-event race without double-posting, because children are themselves edge-triggered. (4) Identity (`==`) filtering means structurally equal but distinct conditions don't cross-trigger. (5) Failure-direction leaves ship as constants: `always(reason)`/`never(reason)` (Conditions facade :53–65) — what handlers fall back to.
**Probe:** No dedicated ConditionSupport test in-tree (coverage caveat recorded honestly); behavior is exercised transitively by DefaultCapabilityReferenceTest's mocked ConjunctionCondition and pinned here by whole-file source read at the commit. Deterministic grep probes with repo-root anchors (re-derived & executed 2026-08-24): `grep -n "if (!active)" public/common/components/nexus-capability/src/main/java/org/sonatype/nexus/capability/condition/ConditionSupport.java` → :80 bind-guard; `grep -c 'this.satisfied != satisfied' <same path>` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "ConditionSupport setSatisfied CompositeConditionSupport reevaluate shouldReevaluateFor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reactive predicate pattern: final idempotent bind/release, edge-triggered state publication, identity-filtered composites, bind-order (children→register→evaluate), and named always/never fallback leaves. Adapt the bus (any pub/sub) and leaf vocabulary. Omit the deprecated EventBus constructors and Nexus-specific leaves (cipher strength, capability-of-type).
