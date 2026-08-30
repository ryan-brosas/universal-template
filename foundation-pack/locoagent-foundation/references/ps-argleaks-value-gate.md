<!-- capsule-v2 -->
# PS argLeaksValue leak channels — how do you prove a cmdlet argument cannot smuggle data or code before auto-allowing it?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Which AST element types and parameter shapes can carry runtime values through an otherwise read-only cmdlet, and what is the canonical rejection function every allowlist entry reuses?

## elementTypes whitelist + colon-bound children[] query = one leak gate
**Path/Symbol:** `src/tools/PowerShellTool/readOnlyValidation.ts`:`argLeaksValue` (:76-115); wired as `additionalCommandIsDangerousCallback` into `write-output`, `write-host`, `start-sleep`, `format-table/list/wide/custom`, `measure-object`, `select-object`, `sort-object`, `group-object`, `where-object`, `out-string`, `out-host`; also enforced inline in `isAllowlistedCommand` (:1380-1427) and `checkPermissionMode` (:297-319, :347-352).
**Signature:** `function argLeaksValue(_cmd: string, element?: ParsedCommandElement): boolean` — true ⇒ dangerous.
**Data Shape:** Reads `element.elementTypes` (index 0 = name; args from 1), `element.args`, `element.children` (per-arg `.Argument` child of colon-bound `CommandParameterAst`, aligned `children[i] ↔ args[i] ↔ elementTypes[i+1]`).

### Decisive source
```ts
for (let i = 0; i < argTypes.length; i++) {
  if (argTypes[i] !== 'StringConstant' && argTypes[i] !== 'Parameter') {
    // ArrayLiteralAst (`Select-Object Name, Id`) maps to 'Other' ... A
    // comma-list of bare identifiers has none [of the metachars].
    if (!/[$(@{[]/.test(args[i] ?? '')) {
      continue
    }
    return true
  }
  if (argTypes[i] === 'Parameter') {
    const paramChildren = children?.[i]
    if (paramChildren) {
      if (paramChildren.some(c => c.type !== 'StringConstant')) {
        return true
      }
    } /* fallback: metachar scan after ':' */
  }
}
```

**Flow:** three leak shapes blocked: (1) bare Variable args — `Write-Output $env:SECRET` prints it, `Start-Sleep $env:SECRET` leaks via type-coerce error text; (2) `'Other'` elements (HashtableAst/ConvertExpressionAst/BinaryExpressionAst) unless the extent text lacks ALL expression metachars `$(@{[` (bare identifier comma-lists like `Select-Object Name, Id` stay allowed); (3) colon-bound expressions — `-InputObject:$env:SECRET` is ONE CommandParameterAst so the whitelist alone passes; the `.Argument` CHILD's mapped type must also be StringConstant. The same triple gate is duplicated inside `isAllowlistedCommand` for non-callback cmdlets (with `elementTypes === undefined` failing CLOSED) because generic entries lack callbacks.
**Invariant:** A user allow rule asserts the CMDLET is safe, never that arbitrary variable expansion THROUGH it is safe — hence the gate applies to user-rule matches too (security finding #32: exact allow on `PowerShell(Write-Output:*)` would otherwise surface `Write-Output $env:ANTHROPIC_API_KEY`). Numeric literals are safe: `ConstantExpressionAst` maps to StringConstant precisely so `-Seconds:5` doesn't false-positive.
**Probe:** `grep -cF "additionalCommandIsDangerousCallback: argLeaksValue" src/tools/PowerShellTool/readOnlyValidation.ts` → `14` (13 cmdlet entries + 1 external-callback composition) and `grep -cF '[$(@{[]' src/tools/PowerShellTool/readOnlyValidation.ts` → `4` (argLeaksValue ×2 + isAllowlistedCommand whitelist & colon fallback; anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "argLeaksValue children colon-bound", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whitelist-plus-children-query shape and its reuse as the shared callback. Adapt the metachar set only with care (the comma-list carve-out depends on exactly these five chars). Omit Bash echo-regex comparison details beyond the pointer. Coverage caveat: no upstream tests in-repo; graph confirms `argLeaksValue` :76-115 rank#1 line-exact.
