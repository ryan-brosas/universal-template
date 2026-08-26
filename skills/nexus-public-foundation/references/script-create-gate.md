<!-- capsule-v2 -->
# Script manager create-gate — how do you ship a script-execution subsystem that is present but disabled by default, and what exactly does the flag gate?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`ScriptManagerImpl.java` 126L whole-file; NO dedicated unit test — coverage caveat); Codebase Memory `nexus-public`. **Question:** Scripts are arbitrary code execution — how does the design let operators keep old scripts runnable while refusing new attack surface?

## nexus.scripts.allowCreation (default FALSE) gates ONLY create/update via validateCreationIsAllowed(); browse/get/delete/run stay available; every mutation posts a lifecycle event
**Path/Symbol:** `public/common/components/nexus-script-plugin/src/main/java/org/sonatype/nexus/script/plugin/internal/ScriptManagerImpl.java` — `@Value("${nexus.scripts.allowCreation:false}") boolean allowCreation` ctor (:54-63), `create()` calls `validateCreationIsAllowed()` FIRST (:76-87), `update()` same (:90-100), ungated `delete()` (:103-110), `isEnabled()` (:112-114), `validateCreationIsAllowed()` throws `ScriptingDisabledException` (:116-120); exception type: `ScriptingDisabledException.java` :20-26 extends RuntimeException.
**Signature:** `Script create(String name, String content, String type) throws ScriptingDisabledException; Script update(String name, String content) throws ScriptingDisabledException; void delete(String name); boolean isEnabled()`.
**Data Shape:** scripts persisted via MyBatis `ScriptStoreImpl` (`@Qualifier("mybatis") ConfigStoreSupport<ScriptDAO>`, every store method `@Transactional`) holding name/content/type where type defaults to `ScriptManager.DEFAULT_TYPE`; manager annotated `@ManagedLifecycle(phase = SERVICES)` + methods `@Guarded(by = STARTED)`.

### Decisive source
```java
// :54-63 — default-deny wiring
@Value("${nexus.scripts.allowCreation:false}")
final boolean allowCreation

// :76-79 — gate placement: BEFORE any store write
public Script create(final String name, final String content, final String type) {
  validateCreationIsAllowed();
  Script script = scriptStore.newScript();
  ...
  eventManager.post(new ScriptCreatedEvent(script));

// :116-120
private void validateCreationIsAllowed() {
  if (!allowCreation) {
    throw new ScriptingDisabledException("Creating and updating scripts is disable");
```

**Flow:** operator sets property (default off) → REST add/edit attempts hit manager → gate throws before persistence → resource layer maps the exception to HTTP 410 GONE with the message body → existing scripts still list/read/run/delete (delete intentionally ungated: removing scripts must never be locked out). Every successful mutation fires Created/Updated/Deleted events for audit/UI.
**Invariant:** (1) The gate is checked BEFORE touching storage and again on update — no code path persists script content while disabled. (2) Delete is deliberately NOT gated: a lockdown that prevents cleanup traps operators. (3) The flag gates WRITE not EXECUTION — running stored scripts is controlled by permission `run`, so disabling creation alone never equals disabling scripting. (4) Typo-tolerant fact: upstream message reads "is disable" verbatim.
**Probe:** no dedicated ScriptManagerImplTest in tree (recorded caveat; behavior pinned indirectly via ScriptResource mapping + security contributor test). Deterministic anchors: `grep -c 'validateCreationIsAllowed' public/common/components/nexus-script-plugin/src/main/java/org/sonatype/nexus/script/plugin/internal/ScriptManagerImpl.java` = 3; `grep -c 'allowCreation:false' public/common/components/nexus-script-plugin/src/main/java/org/sonatype/nexus/script/plugin/internal/ScriptManagerImpl.java` = 1.
**Retrieve:** search_graph project nexus-public query "ScriptManagerImpl allowCreation validateCreationIsAllowed" — resolves Methods :54-63/:76+ line-exact.
**Verdict:** Adopt default-off creation gating with explicit delete-exemption for any embedded-scripting feature. Adapt property naming/exception→HTTP mapping to your stack. Omit nothing behavioral; note missing upstream test when porting (write your own).
