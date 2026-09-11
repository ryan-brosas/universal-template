<!-- capsule-v2 -->
# undocumented-operator admission — how can an operator be parseable and lowerable yet rejected by the SDK's node types?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When a grammar parses an operator the UI never suggests, which layer must admit it before backend lowering works?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb-sdk/src/lib/formula/operators.ts` (:3–:5 ArithmeticOperators gains '%').
**Signature:** `export const ArithmeticOperators = ['+', '-', '*', '/', '%'] as const;`
**Data Shape:** const-asserted tuple feeding parsed-node type guards across SDK consumers.

### Decisive source
```ts
// `%` is undocumented — not in the function list, never suggested by the UI —
// but jsep parses it and the builders lower it, so the node type must admit it.
export const ArithmeticOperators = ['+', '-', '*', '/', '%'] as const;
```

**Flow:** jsep tokenizes `%` regardless of docs → binaryExpressionBuilder lowers `%` (pg: ieeeModuloSql; else MOD mapping) → but typed node guards consult ArithmeticOperators, so WITHOUT the SDK entry a stored `%` formula fails validation/typing upstream of any builder.
**Invariant:** Grammar acceptance lives in three layers (parser / type vocabulary / builder); the type vocabulary is the one persisted artifacts check against — adding builder support without the SDK tuple breaks old columns, not new ones. Undocumented-yet-parseable operators are a compatibility surface, not dead syntax.
**Probe:** `sed -n '1,6p' packages/nocodb-sdk/src/lib/formula/operators.ts` verbatim; consumer lowering pinned at parsed-tree-builder.ts :727–:731 (`%` → ieeeModuloSql on pg). No dedicated spec (caveat).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "ArithmeticOperators formula operators sdk", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt layer-checklist when admitting operators; adapt vocabulary names; omit workflow selectOptions plumbing (UI surface).
