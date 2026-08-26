<!-- capsule-v2 -->
# Tracker singleton + start guards — what one-instance and environment checks gate `start()`?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** Which guards prevent double-tracker bugs, insecure contexts, and unsupported browsers?

## window.__OPENREPLAY__ sentinel, HTTPS enforcement, API checklist, DNT
**Path/Symbol:** `tracker/tracker/src/main/index.ts` — sentinel check (:134–140), HTTPS gate (:141–146), DNT (:147 & :287–294), required-API list (:149–181), `processOptions` (:86–114: projectKey/projectID compat), singleton wrapper `singleton.ts` (`configure` once-guard :14–32, promise normalization :47–53).
**Signature:** `new API(options)` constructor IS the guard chain; `TrackerSingleton.start(): Promise<StartPromiseReturn>`.
**Data Shape:** failure ⇒ console.error + `signalStartIssue('missing_api', [...])`, app stays null; `start()` rejects with reason string.

### Decisive source
```ts
if ((window as any).__OPENREPLAY__ ||
    (!this.crossdomainMode && inIframe() && canAccessTop() && (window.top as any).__OPENREPLAY__)) {
  console.error('OpenReplay: one tracker instance has been initialised already')
  return
}
if (!options.__DISABLE_SECURE_MODE && location.protocol !== 'https:') { ...; return }
```
```ts
const conditions = ['Map','Set','MutationObserver','performance','timing','startsWith','Blob','Worker']
```

**Flow:** configure-once → construct → sentinel scan (own window AND accessible top when iframe) → SSL check (bypassable via `__DISABLE_SECURE_MODE` for localhost) → feature-detect the 8 APIs → DNT respect option → only then instantiate App. Singleton layer additionally converts reject-paths into `{success:false, reason}` so callers never get thrown strings.
**Invariant:** The sentinel is set at the END of construction (:262) — a failed construction must NOT set it, allowing retry after config fixes. projectID (number) auto-upgrades to string projectKey with deprecation warning.
**Probe:** `grep -c 'one tracker instance has been initialised' tracker/tracker/src/main/index.ts` → `1`; `grep -c '__DISABLE_SECURE_MODE' tracker/tracker/src/main/index.ts` → `3`; `grep -c "location.protocol !== 'https:'" tracker/tracker/src/main/index.ts` → `1`; direct tests: main.test/singleton.test suites exist upstream but FAIL TO COMPILE at this pin due to committed merge-conflict markers in top_observer.ts (documented defect — see Boundaries).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "processOptions OPENREPLAY sentinel missing_api doNotTrack", limit: 10 });
```

## Verdict
Adopt guard order (sentinel→SSL→APIs→DNT). Adapt bypass flags. Omit legacy projectID shim.
