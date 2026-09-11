<!-- capsule-v2 -->
# Env-var input surface & GitLab docker-mode injection — how does an env-driven adapter normalize booleans and force native mode?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** How do the non-GitHub adapters read configuration, and when must they override the tool's own docker behavior?

## QODANA_* namespace, def-aware boolean parsing, within-docker=false default injection
**Path/Symbol:** `gitlab/src/utils.ts:getInputs` (:51-95) incl. `getQodanaStringArg`/`getQodanaBooleanArg` (:102-109), `baseDir` (:97-100), push-fixes rename merge-request→pull-request (:62-65); VSTS twin `vsts/src/utils.ts:getInputs` (:73-104, tl.getInput/getBoolInput, AGENT_TEMPDIRECTORY home).
**Signature:** `getQodanaBooleanArg(name: string, def: boolean): boolean`.
**Data Shape:** env names prefixed `QODANA_`; results/cache under `${CI_BUILDS_DIR||tmpdir}/.qodana`.

### Decisive source
```ts
function getQodanaBooleanArg(name: string, def: boolean): boolean {
  const value = process.env[`QODANA_${name}`]?.toLowerCase()
  return def ? value !== 'false' : value === 'true'
}
...
const qodanaDockerEnv = process.env.QODANA_DOCKER ?? ''
if (qodanaDockerEnv === '' && !argList.includes('within-docker')) {
  argList.push('--within-docker', 'false')
}
```
Note the asymmetry with the detector it feeds: `isNativeMode` checks `'--within-docker'` via findIndex + next-token=='false' but the INJECTED form here is the split-token pair, and `includes('within-docker')` (no dashes!) matches both `--within-docker` spellings — a deliberate loose guard against double injection.

**Flow:** every input resolves through the QODANA_-prefixed env with defaults chosen per platform idiom (GitLab defaults MR_MODE=true, POST_MR_COMMENT=true, USE_CACHES=true; commit message carries its own [skip-ci]) → args parsed via shared parseRawArguments → unless QODANA_DOCKER is set or args mention within-docker, inject `--within-docker false` so GitLab jobs run the CLI natively instead of nesting Docker-in-Docker → memoize into module-level cachedInputs.
**Invariant:** Boolean parsing is DEFAULT-AWARE in a way naive parsers get wrong: with def=true, ANYTHING except literal 'false' (case-insensitive, undefined included) is true; with def=false, ONLY literal 'true' is true. The within-docker injection must be skipped when QODANA_DOCKER is present — that env means the user explicitly wants image mode.
**Probe:** no direct tests for gitlab/vsts getInputs (coverage caveat); deterministic probes: ranges above + search_graph "getQodanaBooleanArg within-docker" resolving both twins; boolean semantics cross-checked against common/__tests__ native-prefix expectations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "QODANA_ENV getQodanaBooleanArg baseDir inputs", limit: 6 });
```

## Verdict
Adopt the namespaced-env convention, default-aware tri-state-ish boolean parse, and the explicit opt-out-before-forcing-native pattern; adapt variable names to your CI's conventions; keep the loose substring guard comment-worthy — it looks like a bug and isn't.
