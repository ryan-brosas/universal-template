<!-- capsule-v2 -->
# Position-aware $ref rewrite for the legacy output-schema wrap — how do same-document JSON Pointers keep resolving after a schema is relocated under `properties.result`?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When wrapping a non-object `outputSchema` as `{type:'object', properties:{result:…}, required:['result']}` (2025 wire requirement), which `$ref`s must be rewritten, and which positions and scopes must be left alone?

## Rewrite walker & scope rules
**Path/Symbol:** `packages/core-internal/src/wire/rev2025-11-25/legacyWrap.ts`: data/name-position key sets (:36-53), `establishesNewBase` (:61-63), keyword-coverage block (:65-105), `wrapOutputSchemaForLegacy` (:127-194).
**Signature:** `wrapOutputSchemaForLegacy(natural: Readonly<Record<string, unknown>>): Record<string, unknown>`; rewrite rule: `'#' → '#/properties/result'`, `'#/…' → '#/properties/result/…'`, everything else verbatim.
**Data Shape:** wrapper `{…($schema && {$schema}), type:'object', properties:{result:<natural>}, required:['result']}`; `$schema` HOISTED to the wrapper root (:136) so dialect dispatch still sees it.

### Decisive source
```ts
// :151-166 the position machine
const rewriteRefs = (node: unknown, parentIsNameMap: boolean): unknown => {
    if (!parentIsNameMap && establishesNewBase((node as Record<string, unknown>)['$id'])) return node;
    // …
    if (parentIsNameMap) {
        // Name position: keys are author-chosen names, values ARE subschemas — never keywords
        out[k] = rewriteRefs(v, false);
    } else if ((k === '$ref' || k === '$dynamicRef') && typeof v === 'string') {
        out[k] = v === '#' ? '#/properties/result' : v.startsWith('#/') ? `#/properties/result${v.slice(1)}` : v;
    } else if (REF_REWRITE_DATA_POSITION_KEYS.has(k)) {   // const/enum/default/examples: instance data
        out[k] = v;
```

**Flow:** root `$id` that establishes a base (any non-`#`-prefixed string) ⇒ return the natural schema embedded WHOLE — its internal pointers resolve against the embedded base, not the wrapper. Otherwise walk: data-position values (`const/enum/default/examples`) copied untouched; name-map entries (`properties/patternProperties/$defs/definitions/dependentSchemas/dependencies`) recursed with keys treated as NAMES; nested base-establishing `$id` freezes its subtree; fragment-only `$id` (`"#item"`, draft-07 anchor spelling) does NOT establish a base and IS rewritten; 2019-09 `$recursiveRef:'#'` converts to a static `$ref:'#/properties/result'` ONLY when the declared dialect is 2019-09 AND the document root lacks `$recursiveAnchor:true` (root-anchored recursion stays verbatim — documented mis-resolution limitation), joining via `allOf` when `$ref` co-occurs.

**Invariant:** pointer rewriting is SOUND only while every descended position is provably a subschema — rewriting a `$ref`-shaped STRING inside `enum:`/`const:`/a property named `default` corrupts instance data or silently skips a real subschema. The `$schema` hoist is load-bearing: left under `properties.result`, an Ajv2020 default-engine compile of a draft-07 tuple schema fails opaquely and unsupported-dialect graceful rejection never fires.

**Probe (direct tests):** `packages/core-internal/test/wire/legacyWrap.test.ts` — :16 'rewrites $ref/$dynamicRef in keyword position; leaves data positions (const/enum/default/examples) untouched', :47 'a property NAMED default/const under properties/$defs is a name position', :90 '$id skips the pointer rewrite entirely', :201/:214 fragment-only $ids do not suppress rewriting, :246 'anchor-less $recursiveRef:"#" is converted', :268 'with a $recursiveAnchor in the document, $recursiveRef is left verbatim (documented limitation)'.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "wrapOutputSchemaForLegacy ref rewrite result properties", limit: 3 });
// → rev2025-11-25/legacyWrap.wrapOutputSchemaForLegacy Function 127-194 rank #1
```

## Verdict
Adopt the position-aware walker and $id/$schema scoping wholesale — this is pure JSON-Schema surgery with no host coupling; adapt the target wrapper shape if your wire allows non-object roots (2026 era is identity); omit the $recursiveRef conversion only with a documented engine-behavior caveat.
