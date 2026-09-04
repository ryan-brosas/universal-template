<!-- capsule-v2 -->
# Script REST resource — what is the exact status-code contract for a script API (including the disabled and run-failure cases), and how are per-script permissions shaped?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`ScriptResource.java` 232L whole-file + `ScriptSecurityContributorTest`); Codebase Memory `nexus-public`. **Question:** When a porter exposes stored scripts over REST, which failures map to 404 vs 410 vs 400, where do annotations end and programmatic checks begin, and what does the permission string look like?

## BREAD resource: annotation perms on browse/add, PROGRAMMATIC per-name perms on read/edit/delete/run; disabled⇒410 GONE; eval failure⇒400 with message body; missing⇒404; path/body name mismatch⇒400 via checkArgument
**Path/Symbol:** `public/common/components/nexus-script-plugin/src/main/java/org/sonatype/nexus/script/plugin/internal/rest/ScriptResource.java` — `RESOURCE_URI = "/v1/script"` (:78), `browse()` `@RequiresPermissions("nexus:script:*:browse")` (:101-111), `read()` programmatic `securityHelper.ensurePermitted(scriptPermission(name, READ))` + findOr404 (:113-121), `edit()` name-match checkArgument :134-135 then update catch→410 (:132-146), `add()` @RequiresPermissions add + catch→410 (:148-167), `delete()` programmatic perm + findOr404 (:169-181), `run()` RUN_ACTION perm + eval in try/catch → 400 on ANY exception (:183-216), `findOr404` NotFoundException (:218-226), `scriptPermission()` factory (:228-231).
**Signature:** `public List<ScriptXO> browse(); public ScriptXO read(String name); public void edit(String name, ScriptXO scriptXO); public void add(ScriptXO scriptXO); public void delete(String name); public ScriptResultXO run(String name, String args)`.
**Data Shape:** JSON only; XO records {name,content,type} in, result {name,result} out; custom bindings injected into eval: `log` (class logger), `args` (trimmed-or-null raw string), `scriptName`.

### Decisive source
```java
// :141-145 — disabled mapping (manager threw BEFORE any write)
catch (ScriptingDisabledException e) { // NOSONAR
  throw new WebApplicationException(
      Response.status(Response.Status.GONE)
          .entity(new ScriptResultXO(name, e.getMessage())).build());

// :198-211 — run: capture everything, never leak a stack trace
try {
  Map<String, Object> customBindings = new HashMap<>();
  customBindings.put("log", LoggerFactory.getLogger(this.getClass()));
  customBindings.put("args", args != null ? args.trim() : null);
  customBindings.put("scriptName", script.getName());
  result = scriptService.eval(script.getType(), script.getContent(), customBindings);
  eventManager.post(new ScriptRunEvent(script));
}
catch (Exception e) {
  throw new WebApplicationException(Response.status(Response.Status.BAD_REQUEST)
      .entity(new ScriptResultXO(script.getName(), e.getMessage())).build());
```

**Flow:** request → JAX-RS route → coarse annotation check (browse/add) OR fine-grained programmatic check including the script NAME in the permission (read/edit/delete/run) → manager call → exception translation ladder: not-found=404 (NotFoundException), disabled=410 GONE carrying message entity, execution failure=400 BAD_REQUEST carrying message entity (logged server-side at error), success=200 list/read/result or 204 mutations. Run additionally fires ScriptRunEvent AFTER successful eval.
**Invariant:** (1) Per-name permissions use WildcardPermission2 parts `[nexus, script, <name>]` + action — wildcard `*` in position 3 grants all names; the contributor mints exactly 7 privileges (`nx-script-*-<action>` for browse/read/edit/add/delete/run/all; edit/add privileges imply read). (2) Disabled-state errors are 410 (semantically "resource permanently unavailable by policy"), NOT 403 — porters that map them to 403 break clients that treat 403 as "retry with more rights". (3) Eval exceptions return message text but never class/stack. (4) Path-vs-body name equality is enforced before any write.
**Probe:** `ScriptSecurityContributorTest.java` :38-46 pins the 7 privilege ids (`containsInAnyOrder("nx-script-*-*", ... "-run")`). Deterministic anchor: `grep -c 'Response.Status.GONE' public/common/components/nexus-script-plugin/src/main/java/org/sonatype/nexus/script/plugin/internal/rest/ScriptResource.java` = 2.
**Retrieve:** search_graph project nexus-public query "ScriptResource findOr404 RequiresPermissions" — resolves Methods :101+ line-exact.
**Verdict:** Adopt the status ladder (404/410/400) and dual granularity of authz (annotation for collection ops, per-resource programmatic checks for named ops). Adapt Shiro helpers/JAX-RS types to your host. Omit swagger annotations and extdirect twins.
