<!-- capsule-v2 -->
# GitHub Anonymous-Lock Auth Ladder — when may a registry client ever send credentials to a source that just served content anonymously?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** A GitHub source registry may be public (raw.githubusercontent.com works) or private (only the Contents API with a token/gh works) — what state machine decides which transport reads each file without leaking credentials to public hosts or re-prompting per file?

## anonymous-first read path with root-404-only upgrade
**Path/Symbol:** `packages/shadcn/src/registry/github.ts:createGitHubRegistrySourceReader.readText` (:213-276), `readWithCache` (:170-189), `toGitHubSourceFileError` (:278-353); `packages/shadcn/src/registry/github-auth.ts:getGitHubAuthState` (:35-50), `selectGitHubAuthMode` (:52-66), `decideAndNotify` (:68-88).
**Signature:** `readText(filePath): Promise<string>`; `getGitHubAuthState(anchor: object, source): GitHubSourceAuthState`; `selectGitHubAuthMode(state, source, originalError): Promise<"token" | "gh">`.
**Data Shape:** `GitHubSourceAuthState = { decision?: Promise<mode>, anonymousLock: boolean, originalError?: unknown }`. States live in a module-level `WeakMap<object, Map<sourceKey, state>>` keyed by the command-local `sourceCache` object and sub-keyed by normalized `owner/repo#ref` (lowercased). Mode is `"token"` (env GH_TOKEN/GITHUB_TOKEN via REST Contents API) or `"gh"` (subprocess `gh api`).

### Decisive source
```ts
// github-auth.ts — single-flight decision with rollback on failure:
if (!state.decision) {
  state.originalError = originalError
  state.decision = decideAndNotify().catch((error) => {
    state.decision = undefined   // allow a later retry to decide again
    throw error
  })
}
return state.decision

// github.ts — the ladder inside readText:
if (!authState.anonymousLock && authState.decision) {
  const mode = await authState.decision      // already upgraded → auth read
  ...
}
const content = await readWithCache(`anonymous:${url}`, ...)
if (isRoot) {
  // A public root locks the source so a missing child file never
  // triggers an authenticated request.
  authState.anonymousLock = true
}
...
// Only the initial anonymous ROOT 404 may select an authenticated mode.
if (!isRoot || statusCode !== 404 || authState.anonymousLock) throw error
let mode = await selectGitHubAuthMode(authState, address, error)
```

**Flow:** every file read tries the anonymous raw URL first → if the *root* `registry.json` returns 404 exactly once and the source is not yet locked, `selectGitHubAuthMode` picks token-or-gh once (single-flight promise shared by ref resolution AND content reads), emits one credential notice (awaited context callback or spinner line, deduped process-wide by `notifiedSources`) → from then on all reads for that source go authenticated → but if any anonymous root read SUCCEEDS, `anonymousLock = true` permanently forbids credentials for that source, so child-file 404s surface as ordinary "path does not exist" errors. Authenticated-root-404 deliberately returns `state.originalError` so private-vs-missing stays ambiguous; enoent/unauthenticated during the upgrade keeps the original message plus setup guidance.
**Invariant:** Credentials must only ever reach `api.github.com`, never raw hosts (test asserts raw request carries NO authorization header). At most ONE auth-mode selection and ONE notice per invocation even across concurrent items and separate top-level phases (preflight/catalog/tree). A public source never authenticates, no matter which child file is missing.
**Probe:** `packages/shadcn/src/registry/github.test.ts` — :923-960 upgrade-to-token with token only on api.github.com; :962-985 expired token terminal (no gh fallthrough); :987-1035 gh upgrade exactly once across two concurrent items + one notice; :1037-1071 notice callback awaited before first auth request; :1073-1093 double-404 keeps original anonymous suggestion; :1095-1118 missing child never authenticates (unhandled-request guard); :1120-1147 notice printed once across separate calls. Runner caveat: vitest configured but node_modules absent in the read-only checkout — probes pinned by direct test reads, not executed here.
**Coverage:** github.ts + github-auth.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "anonymousLock selectGitHubAuthMode root registry.json 404 authenticated upgrade", limit: 8 });
// observed: selectGitHubAuthMode #1 (github-auth.ts:52-66), readAuthenticated #2 (github.ts:191-211)
```

## Verdict
Adopt the three-state ladder (anonymous-first, root-404-only upgrade, success-locks-anonymous) plus WeakMap-anchored per-invocation state and single-flight decision with rollback for any multi-transport content client. Adapt the mode pair (token/subprocess) to your transports and move the notice channel behind your own context. Omit shadcn-specific host pinning (`--hostname github.com`) unless you also need hermetic gh runs (see gh-subprocess-hermetic-env-slot).
