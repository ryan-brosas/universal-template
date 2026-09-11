<!-- capsule-v2 -->
# Two-phase Spring component scan — why can every plugin define a bean with the same simple name, and what breaks if you collapse the phases?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`SpringComponentScan.java` 112L + `ApplicationLauncher.java` 115L whole-file); Codebase Memory `nexus-public`. **Question:** How do you wire hundreds of modules into one Spring context when each module was written independently (and several define `internal.UiPluginDescriptorImpl`)?

## Phase 1 scans only bootstrap.entrypoint packages; phase 2 (on ContextRefreshedEvent of the PARENT) scans org|com.sonatype.nexus into a CHILD context using FullyQualifiedAnnotationBeanNameGenerator
**Path/Symbol:** `public/common/components/nexus-bootstrap-spring/src/main/java/org/sonatype/nexus/bootstrap/entrypoint/SpringComponentScan.java` — `ENTRYPOINT_PACKAGES_PATTERN` (:48-49), `JAVA_PACKAGES_FOR_NEXUS_SCANNING` (:51-52), `finishBootstrapComponentScanning()` (:68-92), `getChildContext()` parent-wired bean factory + shared environment (:98-111); `ApplicationLauncher.java` — `@PostConstruct initialize()` edition property-source injection (:67-83), `onContextRefreshed()` parent-only guard (:100-114).
**Signature:** `public ApplicationContext finishBootstrapComponentScanning(); @EventListener public void onContextRefreshed(final ContextRefreshedEvent event)`.
**Data Shape:** child context id `"nexus-spring-component-scan"`; scanner filters: include JSR-330 `@Named`-family (`AnnotationTypeFilter(Named.class)` covers `@Component` via stereotype meta-annotation), exclude entrypoint regex + licensing-ext regex; bean names are Fully Qualified Class Names; autowire mode constructor.

### Decisive source
```java
// ApplicationLauncher :101-106 — only the ROOT context refresh triggers phase 2
if (event.getApplicationContext().getParent() != null) {
  LOG.debug("Application already started, skipping event");
  return;
}

// SpringComponentScan :73-84 — the child-context scan contract
scanner.addIncludeFilter(new AnnotationTypeFilter(Named.class));
scanner.addExcludeFilter(new RegexPatternTypeFilter(ENTRYPOINT_PACKAGES_PATTERN));
scanner.setBeanNameGenerator(new FullyQualifiedAnnotationBeanNameGenerator());
scanner.getBeanDefinitionDefaults().setAutowireMode(AbstractBeanDefinition.AUTOWIRE_CONSTRUCTOR);
scanner.scan(JAVA_PACKAGES_FOR_NEXUS_SCANNING);
childContext.refresh();
```

**Flow:** Spring Boot boots → phase-1 scan registers ONLY `org|com.sonatype.nexus.bootstrap.entrypoint.*` beans (launcher, component-scan orchestrator) → launcher's `initialize()` injects selected edition as first property-source → context refresh fires → `onContextRefreshed` verifies parent==null then runs phase-2 scan → ALL nexus packages scanned into the CHILD context with FQCN bean names → child refresh instantiates the full plugin world (descriptors, stores, managers) which resolve parent beans (edition, properties) through the wired parent factory.
**Invariant:** (1) FQCN bean-name generator is THE mechanism that lets five classes named `UiPluginDescriptorImpl` coexist — switching to annotation/simple-name generation causes ConflictingBeanDefinitionException at boot. (2) The parent-only event guard prevents re-entrant rescans when the child itself publishes ContextRefreshed. (3) Phase separation is load-bearing: entrypoint beans must exist to run the scan, so they cannot be part of what the scan discovers. (4) Child shares the PARENT environment (property sources flow in, never out).
**Probe:** `nexus-bootstrap-spring/src/test/java/org/sonatype/nexus/bootstrap/entrypoint/ApplicationLauncherTest.java` exists; deterministic anchors: `grep -c 'FullyQualifiedAnnotationBeanNameGenerator' public/common/components/nexus-bootstrap-spring/src/main/java/org/sonatype/nexus/bootstrap/entrypoint/SpringComponentScan.java` = 2; `grep -c 'getParent() != null' public/common/components/nexus-bootstrap-spring/src/main/java/org/sonatype/nexus/bootstrap/entrypoint/ApplicationLauncher.java` = 1.
**Retrieve:** search_graph project nexus-public query "SpringComponentScan finishBootstrapComponentScanning" — resolves Methods :56-60/:68+ line-exact.
**Verdict:** Adopt two-phase scanning + FQCN naming for modular monolith hosts where independent modules may collide on simple names. Adapt package regexes to your namespace roots. Omit the licensing-ext exclusion (Sonatype-specific).
