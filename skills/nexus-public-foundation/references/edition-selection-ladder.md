<!-- capsule-v2 -->
# Edition selection — how do you pick ONE product edition from many candidate modules at boot, and how is it forced into the runtime?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`NexusEditionSelector.java` 45L + `NexusEdition.java` 30L + `ApplicationLauncher.mayForceAnalytics`); Codebase Memory `nexus-public`. **Question:** How does the same codebase boot as Community or Pro (or any future flavor) without if/else scattered through core?

## All NexusEdition beans sorted by getPriority() ASC; first isActive() wins; missing ⇒ IllegalStateException; chosen edition becomes a first-in property source
**Path/Symbol:** `public/common/components/nexus-configuration/src/main/java/org/sonatype/nexus/bootstrap/entrypoint/edition/NexusEditionSelector.java` — priority sort in ctor (:33-36), `getCurrent()` first-active-or-throw (:38-44); `NexusEdition.java` — contract `getId/getName/getShortName/getPriority/isActive/getModules` (:17-30); consumer `ApplicationLauncher.initialize()` (:71-82) + `mayForceAnalytics()` (:85-94).
**Signature:** `public NexusEditionSelector(final List<NexusEdition> editions); public NexusEdition getCurrent();` interface: `String getId(); int getPriority(); boolean isActive(); List<String> getModules();`.
**Data Shape:** editions are plain Spring beans (OSS ships `CoreEditionModuleConfiguration` et al under `nexus-repository-core-edition`); selection happens ONCE per boot inside ctor; result exposed to all downstream beans via injected property `nexus.edition`.

### Decisive source
```java
// :33-44 — the whole algorithm
this.editions = new ArrayList<>(editions);
this.editions.sort(Comparator.comparingInt(NexusEdition::getPriority));
}
public NexusEdition getCurrent() {
  return editions.stream()
      .filter(NexusEdition::isActive)
      .findFirst()
      .orElseThrow(() -> new IllegalStateException("No active edition found"));
}

// ApplicationLauncher :77-82 — publish the decision as env
context.getEnvironment().getPropertySources()
    .addFirst(new MapPropertySource("application-launcher",
        Map.of("nexus.edition", nexusEdition)));
```

**Flow:** phase-1 context collects every `NexusEdition` bean → selector sorts ascending by declared priority → `getCurrent()` returns the first whose `isActive()` (classpath/license probe) holds → launcher logs short name, forces CE analytics policy when applicable, injects the object as a FIRST-priority property source so every `@Value("${nexus.edition}")` sees it → UI bundle, features, and modules branch on the selected edition.
**Invariant:** (1) Exactly one edition may be active; two active same-priority editions make selection order-dependent (priorities must be disjoint). (2) No active edition is a HARD boot failure — never silently degrade to a default. (3) The decision is made before phase-2 component scan completes, so plugin modules can rely on it at construction time.
**Probe:** deterministic anchors: `grep -c 'No active edition found' public/common/components/nexus-configuration/src/main/java/org/sonatype/nexus/bootstrap/entrypoint/edition/NexusEditionSelector.java` = 1; `grep -c 'comparingInt' public/common/components/nexus-configuration/src/main/java/org/sonatype/nexus/bootstrap/entrypoint/edition/NexusEditionSelector.java` = 1.
**Retrieve:** search_graph project nexus-public query "NexusEditionSelector getCurrent isActive" — resolves Methods :32-36/:38+ line-exact.
**Verdict:** Adopt collect-DI-list + priority sort + fail-loud single-selection for multi-flavor products. Adapt the activation probe (license checks are Sonatype-specific). Omit CE analytics enforcement unless shipping that license model.
