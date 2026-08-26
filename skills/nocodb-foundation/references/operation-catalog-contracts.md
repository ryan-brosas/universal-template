<!-- capsule-v2 -->
# OperationName catalog & versioned contracts — why does the traced-operation vocabulary live in CE, and what does name@version key?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the registry lookup key, and when must a contract's version bump?

## 169-name enum + three-concern contract
**Path/Symbol:** `packages/nocodb/src/command-registry/op-names.ts:OperationName` (whole 249L, 169 entries) · `command-registry/types.ts:OperationContract` (:21–:54).
**Signature:** flat const object of string-literal twins (`tableCreate: 'tableCreate'`, …) grouped by entity family; contracts add `{version?: number, entry?, undo?|false, sandbox?|false, capture?, capture_schema?, on_record_failure?, macro?}`.
**Data Shape:** `name@version` = registry lookup key AND the `event` column value in `nc_sandbox_changelog`; v1 and v2 coexist until old rows drain.

### Decisive source
```ts
// When adding a new traced operation, add the name here first.
export const OperationName = {
  tableCreate: 'tableCreate',
  // ...
  /** Inverse of a SingleLineText→link conversion: drop the link, recreate
   *  the text column (original id) and restore its backed-up data. */
  columnRevertLinkToText: 'columnRevertLinkToText',
```
(:1–:36)

**Flow:** CE defines names so services annotate without EE imports → EE contracts reference OperationName values → decorator resolves `OperationRegistry.contract(name)` at invocation → changelog rows record name@version → replay resolves the SAME key; schema/replay-semantics changes bump version so stale rows replay under their original contract while it still exists.
**Invariant:** add-the-name-first ordering prevents free-string drift between annotation site and contract registration; inverse-pair ops get BOTH directions named explicitly (columnRevertLinkToText/columnRevertTextToLink carry doc comments stating the exact inverse semantics — porters must keep those comments truthful because they ARE the spec for the inverse builder).
**Probe:** `cd packages/nocodb && grep -cE "^  [a-zA-Z0-9]+: '[a-zA-Z0-9]+'," src/command-registry/op-names.ts` (=169 names) and `grep -n "add the name here first" src/command-registry/op-names.ts` (:15 single directive).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "OperationName columnRevertLinkToText OperationContract macro", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enum-twins + name@version coexistence discipline; adapt the operation vocabulary; omit entirely if no undo/sandbox surface (then drop TraceCommand stubs too — ce-stub-parity-trace.md). Coverage caveat: consumers are EE; CE half is catalog + types.
