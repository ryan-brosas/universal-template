<!-- capsule-v2 -->
# Rapture web-resource bundle — how do you assemble index.html/bootstrap/app.js from plugin descriptors with cache busting and a prod/debug mode switch?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`RaptureWebResourceBundle.java` 488L whole-file + direct test); Codebase Memory `nexus-public`. **Question:** How does the server turn a set of UI plugin descriptors into the actual page resources, and what must a porter not break about ordering, mode, or caching?

## Five generated resources; scripts/styles emitted in priority order; ?debug flips {mode}; cache buster = buildTimestamp or property override, SNAPSHOT adds _dc timestamp
**Path/Symbol:** `public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/internal/RaptureWebResourceBundle.java` — ctor DI of both descriptor lists (:94-130), `getResources()` five-resource bundle (:138-145), `index_html()` (:173-199), `bootstrap_js()` namespaces (:204-227), `app_js()` state+pluginConfigs (:282-304), `generateUrlSuffix()` (:309-328), `isDebug()` request-param probe (:333-336), `getExtJsPluginConfigs()` (:349-358), `getExtJsNamespaces()` (:364-373), `mode()` {mode} substitution (:378-381), `getStyles()` (:412-428), `getScripts()` (:445-475), `getExtJsScripts()` hasScript-gated `-prod.js` (:477-487).
**Signature:** `public List<WebResource> getResources(); private String generateUrlSuffix(); private boolean isDebug(); @VisibleForTesting List<URI> getStyles(); @VisibleForTesting List<URI> getScripts()`.
**Data Shape:** ctor args: `ApplicationVersion`, `Provider<HttpServletRequest>` (per-request debug flag through a singleton!), `Provider<StateComponent>`, `TemplateHelper`, `List<UiPluginDescriptor>` (react), `List<rapture.UiPluginDescriptor>` (extjs), `@Nullable @Value("${nexus.webresources.cachebuster:#{null}}") String cacheBuster`, `boolean analyticsEnabled`. Cache buster defaults to `applicationVersion.getBuildTimestamp()` when property absent (:111-118).

### Decisive source
```java
// :309-328 — the URL suffix contract
buff.append("_v=").append(version);
buff.append("&_e=").append(edition);
buff.append("&_c=").append(this.cacheBuster);
if (version.endsWith("SNAPSHOT")) {
  buff.append("&_dc=").append(System.currentTimeMillis()); // dev: kill cache entirely
}

// :448-474 — script emission ORDER is the contract
scripts.add(uri(mode("baseapp-{mode}.js")));
scripts.add(uri(mode("extdirect-{mode}.js")));
scripts.add(uri("bootstrap.js"));
scripts.addAll(extJsPluginDescriptors.stream()...);   // extjs descriptor scripts
scripts.addAll(pluginDescriptors.stream()...);        // react descriptor scripts (debug-aware)
if (!debug) { scripts.addAll(getExtJsScripts()); }    // prod-only: conventional <id>-prod.js
scripts.add(uri("app.js"));                           // bootstrap LAST: it launches the app
```

**Flow:** HTTP GET /index.html → `TemplateWebResource.generate()` renders velocity template with baseUrl/debug/urlSuffix/styles/scripts → page loads baseapp+extdirect+bootstrap → each descriptor's scripts/styles inline in priority order → app.js last carrying serialized initial `state` JSON + ExtJS `pluginConfigs` class names → bootstrap.js gets ExtJS `namespaces` to require. Debug detection reads the CURRENT request's `?debug` param through the injected `Provider<HttpServletRequest>` even though the bean is a singleton.
**Invariant:** (1) `app.js` MUST be emitted after all descriptor scripts — it boots the app against already-registered namespaces/config classes. (2) In prod mode ExtJS plugin bundles use the CONVENTIONAL path `<pluginId>-prod.js` derived from `getPluginId()` gated on `hasScript()`; renaming a pluginId silently breaks asset resolution. (3) `_v&_e&_c` suffix stability is what makes browser caching correct — a porter that regenerates the suffix per request (instead of per boot) re-downloads everything; a porter that forgets `_dc` on SNAPSHOT ships stale dev caches. (4) Styles order: loading css → baseapp.css → extjs descriptor styles → react styles (test pins this exactly).
**Probe:** `RaptureWebResourceBundleTest.java` :92-126 — `testGetScripts_prod` expects 12 URIs ending `./static/rapture/app.js`; `testGetScripts_debug` :110-126 expects NO `test-*-prod.js` entries and `{mode}`→debug. Byte-exact: `grep -c '_dc=' public/common/components/nexus-rapture/src/main/java/org/sonatype/nexus/rapture/internal/RaptureWebResourceBundle.java` = 1.
**Retrieve:** search_graph project nexus-public query "RaptureWebResourceBundle generateUrlSuffix getScripts" — resolves Methods at :309-328/:444-475 line-exact (verified live).
**Verdict:** Adopt generated-index-from-descriptors, priority-ordered emission, per-request debug switch behind Provider injection, buildTimestamp-defaulted cache buster with property override. Adapt velocity templates and WebResource plumbing. Omit ExtJS-specific extdirect/baseapp conventions unless porting that stack.
