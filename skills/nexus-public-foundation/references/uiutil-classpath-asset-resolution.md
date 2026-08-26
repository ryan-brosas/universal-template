<!-- capsule-v2 -->
# UiUtil classpath asset path resolution — how does a plugin resolve the served URL of a bundled frontend asset when it only knows the filename?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`UiUtil.java` 65L whole-file); Codebase Memory `nexus-public`. **Question:** Multiple plugin jars ship files under `/static/...`; how do you turn a filename into the one web-visible path without hard-coding jar layout?

## Scan classpath:/static/**/<filename> across ALL jars; take FIRST hit; strip everything before the first "/static" so the result is a web-root-relative path; null when absent
**Path/Symbol:** `public/common/components/nexus-ui-plugin/src/main/java/org/sonatype/nexus/ui/UiUtil.java` — `RESOURCE_PREFIX = CLASSPATH_ALL_URL_PREFIX + "/static/**/"` (:36), `@Scope(SCOPE_PROTOTYPE)` prototype bean (:32-34), `getPathForFile(filename)` (:49-64).
**Signature:** `public String getPathForFile(final String filename)` → nullable web path string.
**Data Shape:** input bare filename (`nexus-rapture-bundle.js`); uses Spring's `classpath*:` resolver so EVERY jar's `/static/**` is searched in classpath order, not just the caller's own jar; output like `/static/rapture/nexus-rapture-bundle.js` suitable for prefixing with base URL.

### Decisive source
```java
// :49-59
for (Resource resource : context.getResources(RESOURCE_PREFIX + filename)) {
  URL url = resource.getURL();
  String fullPath = url.getPath();
  if (fullPath.contains("/static")) {
    return fullPath.substring(fullPath.indexOf("/static")); // jar:file:/...!/static/x → /static/x
  }
  return url.getPath(); // exploded classes dir: keep as-is
}
return null;
```

**Flow:** descriptor constructor (e.g. `UiReactPluginDescriptorImpl`) calls `getPathForFile("nexus-rapture-bundle.debug.js")` once at boot → resolver matches the file inside whichever jar carries it → substring at first `/static` yields the container-neutral public path → list frozen into the descriptor and later embedded into index.html script tags.
**Invariant:** (1) The cut point is the LAST-ditch contract: anything before the first `/static` is environment-specific (jar protocol, exploded dir, Windows separators) — porters returning the full filesystem URL serve 404s under servlet containers. (2) First-match-wins means duplicate filenames across jars resolve nondeterministically w.r.t. classpath order — asset names must be globally unique per product convention. (3) Missing asset returns null (descriptor must tolerate) rather than throwing.
**Probe:** deterministic anchors: `grep -c 'indexOf("/static")' public/common/components/nexus-ui-plugin/src/main/java/org/sonatype/nexus/ui/UiUtil.java` = 1; `grep -c 'CLASSPATH_ALL_URL_PREFIX' public/common/components/nexus-ui-plugin/src/main/java/org/sonatype/nexus/ui/UiUtil.java` = 1.
**Retrieve:** search_graph project nexus-public query "UiUtil getPathForFile static" — resolves Method :40-43/:49+ line-exact.
**Verdict:** Adopt classpath-scan + marker-substring resolution for fat-jar web assets. Adapt the prefix constant to your resource root. Omit nothing else — the whole utility is 30 lines of contract.
