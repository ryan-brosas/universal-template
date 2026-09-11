<!-- capsule-v2 -->
# Sed allowlist two-pattern grammar — the only sed programs that auto-approve, and the -e/-w flag-combination throw

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** sed is Turing-complete and can write files (`w`) or execute (`e`) — which exact programs can a validator approve without parsing a full sed language?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/sedValidation.ts` — `validateFlagsAgainstAllowlist` (:13-35), `isLinePrintingCommand` (:44-117), `isPrintCommand` strict regex (:128-133), `isSubstitutionCommand` (:142-238), `sedCommandIsAllowedByAllowlist` composition incl. pattern-2 semicolon ban (:247-301), `hasFileArgs` with hasEFlag flip (:307-379), `extractSedExpressions` with dangerous-flag throw (:388-466).
**Signature:** `sedCommandIsAllowedByAllowlist(command: string, options?: { allowFileWrites?: boolean }): boolean`; `isLinePrintingCommand(command: string, expressions: string[]): boolean`.
**Data Shape:** Pattern 1: `-n` required + every `;`-separated command matches `/^(?:\d+|\d+,\d+)?p$/`. Pattern 2: exactly one expression starting `s`, slash delimiter ONLY (regex `/^s\/(.*?)$/`), exactly 2 unescaped delimiters, flags `/^[gpimIM]*[1-9]?[gpimIM]*$/`.

### Decisive source
```ts
// Reject dangerous flag combinations like -ew, -eW, -ee, -we (combined -e/-w with dangerous commands)
if (/-e[wWe]/.test(withoutSed) || /-w[eE]/.test(withoutSed)) {
  throw new Error('Dangerous flag combination detected')
}
```
And the mode split:
```ts
if (allowFileWrites) {
  // When allowing file writes, only check substitution commands (Pattern 2 variant)
  // Pattern 1 (line printing) doesn't need file writes
  isPattern2 = isSubstitutionCommand(command, expressions, hasFileArguments, { allowFileWrites: true })
} else {
  isPattern1 = isLinePrintingCommand(command, expressions)
  isPattern2 = isSubstitutionCommand(command, expressions, hasFileArguments)
}
```

**Flow:** extract expressions (throw on malformed shell syntax or `-ew`-class bundles ⇒ not allowed) → determine hasFileArgs (with `-e` present, EVERY non-flag arg after it is a file; without, first non-flag arg is the expression and arg #2+ are files) → read-only mode accepts print-programs OR stdout-only substitutions; acceptEdits mode (`allowFileWrites`) accepts substitutions WITH `-i`/`--in-place` + file args but NEVER line-printing-with-writes — then bans semicolons in pattern-2 matches (command separators) and finally runs the denylist battery.

**Invariant:** (1) STRICT ALLOWLIST over language parsing: only `p`, `Np`, `N,Mp` prints and single well-formed `s///flags` with g/p/i/I/m/M/one-digit are approvable — everything else falls to the ask path. (2) The `-e` flag FLIPS argument semantics: with any `-e`, all remaining positionals are FILES (an attacker smuggles `w file` past "first positional is expression" assumptions). (3) Combined-flag rejection happens at extraction time as a THROW, because `-ew 's/a/b/'` would otherwise have its bundle silently accepted by per-character allowlist checks while GNU sed reads `-e w`. (4) allowFileWrites widens EXACTLY one axis (-i + file args) and simultaneously NARROWS another (pattern 1 exits) — mode expansion must be explicit about what it gives up.

**Probe:** no upstream tests reachable (`@internal Exported for testing` markers exist but no test file ships) — coverage caveat. Pins from repo root: `grep -nF "-e[wWe]" src/tools/BashTool/sedValidation.ts` → :398; `grep -nF "isPattern2 && expr.includes(';')" src/tools/BashTool/sedValidation.ts` → :288.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isLinePrintingCommand isSubstitutionCommand hasFileArgs extractSedExpressions", limit: 6 });
// → all four :44/:142/:307/:388 line-exact (total:4)
```

## Verdict
Adopt the two-pattern grammar and the -e/-w throw verbatim. Adapt the acceptEdits wiring to your permission-mode names. Omit nothing if you run sed at all — each restriction maps to a concrete write/exec vector.
