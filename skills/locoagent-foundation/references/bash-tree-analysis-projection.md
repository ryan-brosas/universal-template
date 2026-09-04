<!-- capsule-v2 -->
# TreeSitterAnalysis one-pass projection — quote context, compound structure, operator reality

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What derived data should you extract from a parsed shell AST ONCE so downstream validators never walk the tree again?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/treeSitterAnalysis.ts` — `extractQuoteContext` (:224), `extractCompoundStructure` (:296), `hasActualOperatorNodes` (:421-443), `extractDangerousPatterns` (:448-489), aggregator `analyzeCommand` (:496-506); consumed via `IParsedCommand.getTreeSitterAnalysis()` (ParsedCommand.ts :235-237) and the `ValidationContext.treeSitter` slot.
**Signature:** `analyzeCommand(rootNode, command) → TreeSitterAnalysis` — four projections in one pass.
**Data Shape:** `{ quoteContext, compoundStructure { hasCompoundOperators, hasPipeline, hasSubshell, hasCommandGroup, operators[], segments[] }, hasActualOperatorNodes, dangerousPatterns { hasCommandSubstitution/ProcessSubstitution/ParameterExpansion/Heredoc/Comment } }`.

### Decisive source
```ts
// This is the key function for eliminating the `find -exec \;` false positive.
// Tree-sitter parses `\;` as part of a `word` node (an argument to find),
// NOT as a `;` operator. So if no actual `;` operator nodes exist in the AST,
// there are no compound operators and hasBackslashEscapedOperator() can be skipped.
```

**Flow:** after each parse, ONE walk produces: which characters sat inside which quote context (regex validators consult it instead of re-stripping quotes), top-level compound structure (segments split at REAL operators; control-flow constructs count as single segments while still recursing for inner pipelines/subshells), whether actual `;`/`&&`/`||` OPERATOR NODES exist (escaped `\;` is an argument word — kills the find-exec false positive class), and a dangerous-pattern census. Consumers (bashSecurity validators) take this as optional data and fall back to regex when null.

**Invariant:** (1) Operator-vs-operand identity is a PARSE question — string-level scanners misjudge escaped operators; ask the tree. (2) Extract once, share widely: multiple validators over the same command must not each re-walk (the tree may be deleted/freed after extraction — noted in-source :493-495). (3) Projections must degrade: every consumer handles `null` analysis (legacy path). (4) Segments preserve construct-wholeness: an `if` block is one segment even though its body contains operators.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'find -exec' src/utils/bash/treeSitterAnalysis.ts | head -1` → :416; `grep -nF 'must be extracted before tree.delete' src/utils/bash/treeSitterAnalysis.ts` → :494; graph resolves analyzeCommand :496-506 + hasActualOperatorNodes :421-443 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "analyzeCommand extractQuoteContext extractCompoundStructure extractDangerousPatterns", limit: 5 });
```

## Verdict
Adopt the one-pass projection bundle pattern: parse once, project the four views, pass them alongside the raw text to every validator.
