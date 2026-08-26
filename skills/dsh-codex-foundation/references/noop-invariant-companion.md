<!-- capsule-v2 -->
# No-op invariant companion — when should a package declare that it owns NO runtime invariant, and how is that recorded structurally?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** if a host scans installed packages for invariant checkers, how does a package whose safety lives entirely inside its own operations register an explicit, documented "nothing to scan" instead of being silently skipped?

## invariant.ts — deliberate empty installer
**Path/Symbol:** `src/invariant.ts:9-28 PACKAGE_NAME` / `name` / `inject` / `install` / `apply` (whole module, 28 lines).
**Signature:** `export const apply = (ctx: Context): Promise<() => void> => Promise.resolve(ctx.invariants.register(PACKAGE_NAME, install))` with `const install: InvariantInstaller = () => {}`.
**Data Shape:** a second Cordis plugin distinct from the main bundle: `name = 'openai-codex-invariant'`, `inject = ['invariants']`, package id `'dsh-codex'`; registers one installer that intentionally does nothing and returns the registration's disposer.

### Decisive source
```ts
// No runtime invariant: the LLM and web registries own provider uniqueness and disposal,
// while credentials and model replies cross file/network boundaries whose
// validation runs in their owning operations. There is no separate mutable
// package relationship to scan.
const install: InvariantInstaller = () => {}
```

**Flow:** host composes the invariants service → companion plugin activates → `apply` registers the empty installer under the package id → the registry records ownership (and a disposer) even though no check exists → disposal unregisters symmetrically.
**Invariant:** the rationale lives IN the source next to the empty body — provider uniqueness/disposal is owned by the LLM and web registries; credential files and model replies are validated at their owning operations (store parse gates, response codecs), so there is no separate mutable package relationship for an external checker to scan. The companion ships as its own build entry (`tsdown.config.ts` node entries: index, invariant, tui, bin), keeping the "nothing to scan" declaration loadable without pulling the provider bundle.
**Probe:** no dedicated upstream spec exists — honest caveat. The nearest behavioral evidence is indirect: tests/loader-composition.spec.ts proves the sibling main entry loads/unloads cleanly through a real Loader, and the module's own type contract (`InvariantInstaller`) is exercised by registration returning a disposer. Treat this capsule as source-architecture evidence, not test-pinned behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "dsh-codex\\.src\\.invariant", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern of registering an explicit empty invariant installer whose comment names which owning operation validates each risk, shipped as a separate entry so the declaration is independently loadable. Adapt package-id naming and your host's invariant-registry API. Omit inventing token checks just to appear compliant — an undocumented gap and a documented no-op are not equivalent. Coverage: src/invariant.ts no_recorded_issue + metadata_match; no dedicated upstream spec (recorded caveat).
