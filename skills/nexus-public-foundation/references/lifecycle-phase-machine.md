<!-- capsule-v2 -->
# ManagedLifecycle phase machine — in what order do subsystems start, what happens when one fails, and how do you cap startup below full boot?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`NexusLifecycleManager.java` 231L + `ManagedLifecycle.java` 45L + `NexusServletContextListener.java` 123L whole-file); Codebase Memory `nexus-public`. **Question:** How does the server sequence KERNEL→…→TASKS component starts so dependencies exist before dependents, without letting a broken optional task abort boot?

## 11 ordinal phases; forward start / reverse stop via Multimap; TASKS-phase failures only warn (propagate=false); nexus.lifecycle.startupPhase caps how far boot climbs; bounce() re-runs a phase by stepping back one
**Path/Symbol:** `public/common/components/nexus-common/src/main/java/org/sonatype/nexus/common/app/ManagedLifecycle.java` — `enum Phase {OFF, KERNEL, STORAGE, RESTORE, UPGRADE, SCHEMAS, EVENTS, SECURITY, SERVICES, REPOSITORIES, CAPABILITIES, TASKS}` (:27-41); `public/common/components/nexus-extender-spring/src/main/java/org/sonatype/nexus/extender/NexusLifecycleManager.java` — `to(targetPhase)` synchronized walk (:81-121), `bounce()` (:124-137), `startComponent(...,propagateErrors)` (:142-159), `stopComponent` (:163-180), `delayStartUpTask` single-thread scheduler (:182-194), `getLifecyclesInPhase` priority sort + CGLIB unwrap (:197-224), `getPriority` default 0 (:219-222), proxy unwrap (:224-228); servlet listener: `contextInitialized`→`moveToPhase(TASKS)` (:71-81), `moveToPhase` cap (:115-122).
**Signature:** `public synchronized void to(final Phase targetPhase) throws Exception; public void bounce(final Phase bouncePhase) throws Exception; private void startComponent(final Phase phase, final Lifecycle lifecycle, final boolean propagateErrors)`.
**Data Shape:** components registered per phase in a `HashMultimap<Phase, Lifecycle>`; annotation `@ManagedLifecycle(phase=...)` on any Spring `Lifecycle` bean; ordering inside a phase = `jakarta.annotation.Priority` DESC (default 0). Startup delay for tasks from `FeatureFlags.STARTUP_TASKS_DELAY_SECONDS_VALUE`.

### Decisive source
```java
// :100-109 — error policy differs BY PHASE
boolean propagateNonTaskErrors = !TASKS.equals(nextPhase);
for (Lifecycle entry : lifeCyclesInPhase.get(nextPhase)) {
  if (nextPhase.equals(TASKS) && timeToDelay > 0) {
    delayStartUpTask(nextPhase, entry, propagateNonTaskErrors);
  } else {
    startComponent(nextPhase, entry, propagateNonTaskErrors);
  }
}
currentPhase = nextPhase;

// :115-122 (listener) — the startup cap
private void moveToPhase(final Phase phase) throws Exception {
  if (startupPhase != null && phase.ordinal() > startupPhase.ordinal()) {
    nexusLifecycleManager.to(startupPhase); // this far, no further
```

**Flow:** webapp contextInitialized → check `nexus.lifecycle.startupPhase` property (optional ceiling) → `to(TASKS)` walks phases in ordinal order starting each `@ManagedLifecycle` bean within its phase in priority order → non-TASKS failure throws (boot aborts loudly) → TASKS-phase failures log warn and continue → contextDestroyed logs uptime then `to(OFF)` stopping everything in reverse. `bounce(P)` steps back to P−1 and re-enters P (KERNEL bounce sets `karaf.restart` legacy flag).
**Invariant:** (1) A component's phase is a DEPENDENCY CONTRACT: anything needing storage must be ≥STORAGE; you cannot reference beans that start later. (2) Once `isShuttingDown()`, `to()` cannot move backwards — shutdown is one-way. (3) Only TASKS tolerates failed components; treating another phase as optional silently ships a half-booted server. (4) Annotation lookup unwraps `$$SpringCGLIB$$` proxies first or AOP-proxied lifecycles appear unannotated and never start.
**Probe:** deterministic anchors (no dedicated lifecycle-manager test in OSS tree): `grep -c 'propagateNonTaskErrors' public/common/components/nexus-extender-spring/src/main/java/org/sonatype/nexus/extender/NexusLifecycleManager.java` = 3; `grep -c 'CAPABILITIES' public/common/components/nexus-common/src/main/java/org/sonatype/nexus/common/app/ManagedLifecycle.java` = 1 (the enum constant; the phase name appears exactly once). Cross-capsule tie: railway-nexus3-foundation's bootstrap-once-gate waits out exactly this climb.
**Retrieve:** search_graph project nexus-public query "NexusLifecycleManager ManagedLifecycle Phase" — resolves Methods :66-73/:81+ line-exact.
**Verdict:** Adopt ordinal phase enum + per-phase error policy + startup-phase cap for any server with ordered subsystem bring-up. Adapt the delay mechanism (here a throwaway single-thread scheduler per delayed task). Omit karaf.restart compatibility.
