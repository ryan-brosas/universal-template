<!-- capsule-v2 -->
# Schema validate — bidirectional minimatch glob + @role matching over parent/children allowlists

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How are legal parent/child block relations expressed and enforced, including wildcard and role-based rules?

## Schema.validate / _validateParent / _matchFlavourOrRole
**Path/Symbol:** `blocksuite/framework/store/src/schema/schema.ts`: `validate` (:58-103), `_validateParent` (:172-227), `_matchFlavourOrRole` (:139-163).
**Signature:** `validate(flavour, parentFlavour?, childFlavours?): void` throws `SchemaValidateError`; `safeValidate` swallows to boolean.
**Data Shape:** registered schema = `{version, model: {role, flavour, parent?: string[], children?: string[], ...}}`; entries in `parent`/`children` may be literal flavours (`'affine:note'`), globs (`'affine:note-*'`), roles (`'@content'`), or `'*'`.

### Decisive source
```ts
// the match is BIDIRECTIONAL — either side may carry the glob/role
private _matchFlavour(childFlavour: string, parentFlavour: string) {
  return minimatch(childFlavour, parentFlavour) || minimatch(parentFlavour, childFlavour);
}
// role form: '@x' on one side compares against the OTHER side's concrete role
if (isChildRole) return childValue === `@${parentRole}`;
if (isParentRole) return parentValue === `@${childRole}`;
```
```ts
// structural rules enforced BEFORE relation check
if (schema.model.role === 'root') {
  if (parentFlavour) throw new SchemaValidateError(..., 'Root block cannot have parent.');
  ...
}
if (!parentFlavour) throw new SchemaValidateError(..., 'None root block must have parent.');
```

**Flow:** look up child schema → root-with-parent or non-root-without-parent throws → resolve parent schema → `validateSchema(child, parent)` runs `_validateParent`: cross-product of parent's `children` list × child's `parent` list where EVERY pair must agree via `_matchFlavourOrRole` (`'*'×'*'` auto-passes; single-`'*'` falls back to matching the other side's concrete flavour/role) → then children flavours validated as would-be grandchildren.

**Invariant:** (1) BOTH lists must agree — a child naming `'@content'` under a parent whose `children` is `['affine:paragraph']` FAILS even though the role resolves, because the pair check requires both sides. (2) `role === 'root'` is special-cased twice (no parent; appears only once per workspace); `_validateRole` re-throws inside relation checks so nested validation cannot smuggle a root under a parent. (3) Globs compile through minimatch on EVERY call — hot paths should pre-resolve allowed sets.

**Probe:** `blocksuite/framework/store/src/__tests__/schema.unit.spec.ts` :143-161 ('should glob match works') pins `'affine:note-*'` accepting `note-block-video` while rejecting the non-matching invalid flavour via console.error spy; :109-141 pins role-based parenting and root violations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "Schema validate _validateParent _matchFlavourOrRole minimatch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-list agreement + glob/role vocabulary; adapt error reporting; omit minimatch for a static allowlist if dynamic flavour families are not needed.
