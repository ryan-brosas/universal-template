<!-- capsule-v2 -->
# Parser abort sentinel — three-state parse result where abort ≠ unavailable

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When your static analyzer times out or blows its resource budget on adversarial input, how do you keep that failure from silently downgrading to a weaker code path?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/parser.ts` — `MAX_COMMAND_LENGTH = 10000` (:19), `PARSE_ABORTED` sentinel (:86-93), `parseCommandRaw` (:104-136); `src/utils/bash/bashParser.ts` — `PARSE_TIMEOUT_MS = 50` (:29), `MAX_NODES = 50_000` (:32), no-op `ensureParserInitialized` (:39-41).
**Signature:** `parseCommandRaw(cmd) → Node | null | typeof PARSE_ABORTED` — `Node` = parsed, `null` = module not loaded / feature off / empty / over-length, `PARSE_ABORTED` = loaded but aborted (timeout/node-budget/panic).
**Data Shape:** `TsNode = { type, text, startIndex, endIndex, children }` with **UTF-8 BYTE offsets**, not JS string indices (bashParser.ts :4-6).

### Decisive source
```ts
// SECURITY: Sentinel for "parser was loaded and attempted, but aborted"
// (timeout / node budget / Rust panic). Distinct from `null` (module not
// loaded). Adversarial input can trigger abort under MAX_COMMAND_LENGTH:
// `(( a[0][0]... ))` with ~2800 subscripts hits PARSE_TIMEOUT_MICROS.
// Callers MUST treat this as fail-closed (too-complex), NOT route to legacy.
export const PARSE_ABORTED = Symbol('parse-aborted')
```

**Flow:** length/empty pre-gate returns `null` → await idempotent init → parse under a 50 ms wall-clock deadline + 50k node budget → a `null` FROM THE MODULE means ABORT (not absence): log `tengu_tree_sitter_parse_abort {panic}` and return the symbol. The consumer (`parseForSecurityFromAst`, ast.ts :444-457) maps `PARSE_ABORTED → too-complex → ask`; ONLY genuine `null` maps to `parse-unavailable` (legacy conservative path). The parser itself is pure TypeScript producing tree-sitter-bash-compatible ASTs, validated against a 3,449-input golden corpus generated from the WASM predecessor (header comment :1-10).

**Invariant:** (1) Abort must be distinguishable from unavailability — collapsing them routes adversarial input to the legacy validator, which lacks the semantic builtin blocklists (`trap`/`enable`/`hash` leaked under `Bash(*)` prefixes; verbatim incident comment parser.ts :117-119). (2) Fail CLOSED on abort: an unparseable command must require approval, never fall through to a weaker checker. (3) The 10k char limit does NOT bound parse cost — nested arithmetic subscripts are explosively deep, hence the wall-clock + node-budget dual guard (`Infinity` timeout allowed only for correctness tests, bashParser.ts :24-29). (4) Init shims stay no-op so callers written against an async loader keep working unchanged (API-compatibility stubs, bashParser.ts :38-41).

**Probe:** coverage caveat — no upstream unit tests reachable (tests/ holds shell scripts only). Deterministic pins: `grep -nF 'Callers MUST treat this as fail-closed' src/utils/bash/parser.ts` → :91; `grep -nF 'MAX_NODES = 50_000' src/utils/bash/bashParser.ts` → :32; `grep -nF "Symbol('parse-aborted')" src/utils/bash/parser.ts` → :93; graph `search_graph --project locoagent --query parseForSecurityFromAst` → ast.ts :400-460 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "parseForSecurityFromAst PARSE_ABORTED parseCommandRaw", limit: 5 });
```

## Verdict
Adopt the THREE-state result contract (ok / unavailable / aborted-with-fail-close) for any security-relevant static analysis with resource limits. Adapt limits to your host; never let a timeout downgrade the security tier.
