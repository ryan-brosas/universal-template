<!-- capsule-v2 -->
# PS parser transform layer — how does raw PS1 JSON become typed TS AST shapes without losing security-relevant node kinds?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Which mappings in the raw→typed transform carry security semantics, and which redirection sources must be merged to keep file writes visible?

## mapElementType consolidation + statement-level redirection dedupe
**Path/Symbol:** `src/utils/powershell/parser.ts`:`mapElementType` (:749-796), `mapStatementType` (:712-745), `transformCommandAst` (:830-935), `transformStatement` (:1002-1103), `transformRedirection` (:962-998), `ensureArray` (:703-708).
**Signature:** `function mapElementType(rawType: string, expressionType?: string): CommandElementType`; `function transformStatement(raw: RawStatement): ParsedStatement`.
**Data Shape:** Raw: `.GetType().Name` strings from the PS script. Typed: 8-member CommandElementType / 15-member StatementType unions.

### Decisive source
```ts
case 'SubExpressionAst':
case 'ArrayExpressionAst':
  // SECURITY: ArrayExpressionAst (@()) is a sibling of SubExpressionAst,
  // not a subclass. Both evaluate arbitrary pipelines with side effects:
  // Get-ChildItem @(Remove-Item ./data) runs Remove-Item inside @().
  // Map both to SubExpression so hasSubExpressions fires and isReadOnlyCommand
  // rejects (it doesn't check nestedCommands, only pipeline.commands[]).
  return 'SubExpression'
case 'ParenExpressionAst':
  return 'SubExpression'
```

**Flow:** element mapping consolidates hostile shapes onto flagged types (Array/Paren → SubExpression; Member+InvokeMember → MemberInvocation; ConstantExpressionAst numerics → StringConstant so `-Seconds:5` doesn't false-positive; CommandExpressionAst DELEGATES to its wrapped expressionType so inner ScriptBlocks/SubExpressions surface); non-pipeline statements get a synthetic full-text command entry; redirections merge from THREE sources — per-element, deep FindAll inside pipelines (`-Name:('payload' > file)`, hashtable values), and direct FindAll on control-flow statements where CommandExpressionAst redirections are SIBLING-not-child nodes — deduped by `operator\0target` because FindAll re-discovers element-level ones.
**Invariant:** Every consolidation choice is deny-biased: collapsing MORE raw types into a flagged type can only over-ask, never bypass. The deliberate double-count of nested-command redirections is harmless by contract ("no code does arithmetic on redirection counts") — consumers only test length > 0. PS5.1's array-unwrapping JSON quirk is absorbed once in ensureArray.
**Probe:** `grep -nF 'r.operator' src/utils/powershell/parser.ts | head -2` → :1038/:1041 (the NUL-keyed dedupe Set) and `grep -nF "Map both to SubExpression" src/utils/powershell/parser.ts` → :761 (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "transformStatement mapElementType transformRedirection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the consolidation table with per-case security rationale and the three-source redirect merge with NUL-keyed dedupe. Adapt unions to your grammar. Omit PS-version lore beyond ensureArray. Coverage caveat: probes deterministic; graph confirms all four transforms line-exact.
