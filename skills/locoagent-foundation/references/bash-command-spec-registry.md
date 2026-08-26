<!-- capsule-v2 -->
# Fig spec registry — LRU-cached command metadata for prefix building

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you source per-command argument metadata (subcommands, dangerous args, wrapper markers) to drive smart permission prefixes?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/registry.ts` — `CommandSpec`/`Argument`/`Option` types (:4-28), `loadFigSpec` guard ladder (:30-43), `getCommandSpec = memoizeWithLRU(...)` (:44-53, local specs first, then dynamic `@withfig/autocomplete/build/<cmd>.js` import); consumers `src/utils/bash/prefix.ts` (`getCommandPrefixStatic` :28-70, `isKnownSubcommand` disambiguation :18-26, WRAPPER_COMMANDS) + `src/utils/shell/specPrefix.buildPrefix` (:88-137).
**Signature:** `getCommandSpec(command) → Promise<CommandSpec | null>` (memoized by command name).
**Data Shape:** `Argument.isCommand` marks wrapper slots (timeout/sudo), `isDangerous` flags risky args, subcommand lists drive two-word prefixes.

### Decisive source
```ts
if (!command || command.includes('/') || command.includes('\\')) return null
if (command.includes('..')) return null
if (command.startsWith('-') && command !== '-') return null

try {
  const module = await import(`@withfig/autocomplete/build/${command}.js`)
  return module.default || module
} catch {
  return null
}
```

**Flow:** a command's spec resolves from the curated local table OR the fig autocomplete corpus (path-sanitized: no slashes/dotdot/leading-dash before dynamic import); specs classify commands as WRAPPERS (`isCommand` args ⇒ recurse into the wrapped command when building prefixes, capped at wrapperCount>2 / depth>10) unless the first arg matches a KNOWN SUBCOMMAND (disambiguates `git`-style aliases). Compound prefix suggestions collapse per-root via word-aligned longest-common-prefix (`git fetch`+`git worktree` → `git`; `npm run test`+`npm run lint` → `npm run`). Prefix.ts is the UI/suggestion tier — deliberately heuristic, downstream of the security tier.

**Invariant:** (1) Dynamic module paths need a strict name sanitizer BEFORE interpolation into an import. (2) Wrapper detection must consult the spec, not a hardcoded list alone; but known-subcommand presence overrides wrapper-ness. (3) Recursion budgets (depth ≤10, ≤2 wrappers) bound pathological nesting. (4) This plane is advisory: it shapes what rules users are OFFERED — never a gate.

**Probe:** coverage caveat — no upstream unit tests; `getCommandSpec` is a memoized const arrow (BM25-invisible in graph — cite file:line). Pins: `grep -nF "withfig/autocomplete" src/utils/bash/registry.ts` → :38; `grep -nF 'isKnownSubcommand' src/utils/bash/prefix.ts | head -1` → :18; `grep -nF 'word boundaries' src/utils/bash/prefix.ts` → :178.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "buildPrefix getCompoundCommandPrefixesStatic longestCommonPrefix", limit: 5 });
```

## Verdict
Adopt for prefix-suggestion quality: local-spec-first resolution with sanitized dynamic fallback and wrapper recursion. The LCP collapse rule transfers to any command-palette UX.
