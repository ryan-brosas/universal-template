<!-- capsule-v2 -->
# Auth-adapter discovery — static package.json manifest scan that keeps subscription billing out of child processes

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Child processes are launched with `--no-extensions` for hygiene — but provider auth adapters inject subscription billing headers via their extension hooks, so stripping ALL extensions silently rebills subscription usage as pay-as-you-go (#94). How do you find and re-admit exactly those extensions without executing anything?

## detectAuthAdapterExtensionPaths
**Path/Symbol:** `src/handlers/pi-child-process.ts:detectAuthAdapterExtensionPaths` (:198–212), `scanRootForAuthAdapters` (:160–190), `readPackageExtensionEntries` (:137–158), `isAuthAdapterPackageName` (:127–132); patterns (:114–125): `/(^|[-/])oauth-adapter$/`, `/(^|[-/])auth-adapter$/`, plus exact-name set `{ "pi-claude-auth", "@gotgenes/pi-anthropic-auth" }`; roots default to [own package parent, `AGENT_ROOT/npm/node_modules`] with dedupe.
**Signature:** `detectAuthAdapterExtensionPaths(roots?) → string[]` (resolved extension entry paths).
**Data Shape:** input is directory trees of npm packages (scoped orgs one level deep); output is a deduped list of existing file paths declared in each matching package's `"pi": { "extensions": [...] }` manifest field.

### Decisive source
```ts
// pi has no runtime API to enumerate loaded extensions or map a registered
// provider back to its extension file, so we can't ask pi "what adapter is
// active" directly. Instead we mirror pi's OWN static package-discovery
// convention (package.json -> "pi": { "extensions": [...] }, the same field
// pi-hermes-memory's own package.json declares) and match sibling package
// names against a naming convention, so a future xai-oauth-adapter or
// pi-codex-oauth-adapter is picked up automatically without a code change
// here — no code execution, just JSON reads of sibling package.json files.

function readPackageExtensionEntries(packageDir: string): string[] {
  // parse package.json → manifest?.pi?.extensions (array of relative strings)
  // resolve each against packageDir; keep ONLY paths that existSync
}

function scanRootForAuthAdapters(root: string): string[] {
  // readdir(root): entries starting with "@" → descend ONE level (scoped orgs),
  //   test `${org}/${pkg}` against patterns; plain names tested directly;
  //   matches contribute their declared extension entries
}
```
The pre-convention exact set stays EXACT deliberately: "Keep this list exact so an arbitrary suffixless *-auth package cannot access child maintenance prompts."
**Flow:** (1) `childExtensionPaths` builds the final `-e` list as `[own extension path, config.childExtensionPaths, ...detectedAdapters]` deduped by resolved path and filtered by existence (:214–231); (2) every launch appends `--no-extensions` first, then one `-e` per admitted extension (:233–240) — the retry path uses the identical admission list so both attempts see the same providers.
**Invariant:** discovery is READ-ONLY (JSON parsing only — no code execution from scanned packages); the naming-convention allowlist errs toward MISSING an adapter (billing bug) over admitting an arbitrary `*-auth` package (security boundary: these extensions gain access to maintenance-child sessions). Dedup happens on RESOLVED paths, not raw strings.
**Probe:** `tests/handlers/pi-child-process.test.ts` — points `roots` at fixture directories asserting scoped-org scanning, pattern vs exact-set matching, existence filtering of declared entries, and root dedupe. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "detectAuthAdapterExtensionPaths scanRootForAuthAdapters readPackageExtensionEntries", limit: 5 })`

## Verdict
Adopt whenever a sanitized child environment must selectively re-admit capability-carrying plugins discovered statically. Adapt the pattern list / exact set to your ecosystem's naming conventions. Omit nothing — the security reasoning in the comments IS the design.
