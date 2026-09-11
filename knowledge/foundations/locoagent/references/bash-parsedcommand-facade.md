<!-- capsule-v2 -->
# ParsedCommand facade — tree-sitter/regex duality with size-1 promise cache

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you expose one command-parsing API across an AST implementation and a deprecated regex fallback without callers knowing which ran?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/ParsedCommand.ts` — `IParsedCommand` (:21-32), `RegexParsedCommand_DEPRECATED` (:42-99), `TreeSitterParsedCommand` byte-offset redirection splicing (:211-226), availability memo `getTreeSitterAvailable` (:240-248), `buildParsedCommandFromRoot` (:255-268, parse-once sharing), size-1 cache (:292-318).
**Signature:** `ParsedCommand.parse(command) → Promise<IParsedCommand | null>`.
**Data Shape:** interface: originalCommand / toString / getPipeSegments / withoutOutputRedirections / getOutputRedirections / getTreeSitterAnalysis (null on regex side).

### Decisive source
```ts
// Single-entry cache: legacy callers (bashCommandIsSafeAsync,
// buildSegmentWithoutRedirections) may call ParsedCommand.parse repeatedly
// with the same command string. Each parse() is ~1 native.parse + ~6 tree
// walks, so caching the most recent command skips the redundant work.
// Size-1 bound avoids leaking TreeSitterParsedCommand instances.
```

**Flow:** availability probed once via a real `parseCommand('echo test')` memo; AST path builds from a PRE-PARSED root so security-tier parses are shared (no double parse); pipe positions and redirection NODES come from the tree — redirection removal splices UTF-8 BYTE ranges in descending start order over a Buffer (byte offsets, not JS indices — multi-byte safety); regex twin reimplements the same surface with shell-quote + extractOutputRedirections. The memo caches exactly the last command's PROMISE (dedupes concurrent identical calls) and no more.

**Invariant:** (1) Both implementations must satisfy ONE interface so permission code stays tier-agnostic; the deprecated one returns `getTreeSitterAnalysis() = null` and every consumer must handle that. (2) Redirection splicing operates on byte spans sorted DESCENDING so earlier excisions don't shift later ones. (3) Cache the PROMISE, not the result — concurrent same-command callers share one parse; bound the cache to 1 to avoid holding parsed trees alive. (4) Parse-once-and-share (`buildParsedCommandFromRoot`) is the contract glue between the security tier and this facade.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'Size-1 bound avoids leaking' src/utils/bash/ParsedCommand.ts` → :296; `grep -nF 'skip the redundant native.parse' src/utils/bash/ParsedCommand.ts` → :252; graph resolves buildParsedCommandFromRoot :255-268 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "buildParsedCommandFromRoot ParsedCommand RegexParsedCommand", limit: 5 });
```

## Verdict
Adopt the facade pattern for tiered parsers; the byte-span splice ordering and promise-cache rules transfer directly.
