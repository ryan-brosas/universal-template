<!-- capsule-v2 -->
# Structural walker allowlist — unknown node type ⇒ too-complex

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How should a security AST walker treat grammar constructs it never anticipated?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/ast.ts` — `STRUCTURAL_TYPES` (:54-59), `SEPARATOR_TYPES` (:65), folded ERROR-node handling (:462-465), default branch `tooComplex(child)` in walkCommand (:1311-1312), `tooComplex` reason factory (:2033-2043).
**Signature:** `collectCommands(node, commands, varScope) → ParseForSecurityResult | null` — null = success.
**Data Shape:** recursion over STRUCTURAL_TYPES (program/list/pipeline/redirected_statement); every OTHER node type must be explicitly handled or rejected.

### Decisive source
```ts
// ERROR-node check folded into collectCommands — any unhandled node type
// (including ERROR) falls through to tooComplex() in the default branch.
// Avoids a separate full-tree walk for error detection.
```

**Flow:** walker recognizes: leaf commands, redirected statements, comments, the four structural composites, negated commands (`! cmd` recurses), declaration commands (export/declare/readonly/local/typeset — previously fell through to too-complex; now validated via walkVariableAssignment so `Bash(export:*)` rules match). Inside walkCommand each child type is CASED; the DEFAULT branch returns too-complex naming the offending node type. Arithmetic, test expressions, heredocs/herestrings, file redirects, strings and substitutions each get dedicated walkers that either resolve safely or bail to too-complex.

**Invariant:** (1) Allowlist, never blocklist: an unhandled grammar node is a REJECTION with a diagnostic reason, not a best-effort interpretation — new shell syntax fails closed until modeled. (2) Folding error detection into the single walk keeps one traversal and can't miss subtrees a separate check might skip. (3) Every rejection carries its nodeType for telemetry (`nodeTypeId` maps to numbers) so operators can see WHICH constructs force asks. (4) Expanding the allowlist (declaration_command case) is how false-positive rates drop WITHOUT weakening guarantees.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'folded into collectCommands' src/utils/bash/ast.ts | head -1` → :463; `grep -n "declaration_command" src/utils/bash/ast.ts | head -1` → :579; `grep -nF 'function tooComplex' src/utils/bash/ast.ts` → :2033; graph resolves parseForSecurityFromAst :400-460 whose walkProgram anchors this design.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "collectCommands walkProgram tooComplex STRUCTURAL_TYPES", limit: 5 });
```

## Verdict
Adopt for any security-directed tree walker: explicit case per known construct, default = reject-with-reason. The declaration-command rescue shows the safe way to grow coverage.
