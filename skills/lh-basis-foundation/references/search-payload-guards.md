<!-- capsule-v2 -->
# Search payload guards — How are search-list requests and facet filters validated (and why so shallowly)?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** what does the kernel actually check about a search request, its facet options, and in/nin value sets?

## Minimal request-holder + facet-option duality
**Path/Symbol:** `core/public-methods/shared-types/profilesSearch/guards.js` — `isProfileSearchOption` (11–14), `isISearchListData` (15–18), `isIPeopleSearchListData` (19–21), `isIOrganizationsSearchListData` (22–24), `isProfileSearchOptionOrText` (25–27); `core/public-methods/shared-types/common/guards.js:isISearchDataInNin` (6–11).
**Signature:** `(data): boolean` for all five.
**Data Shape:** search-list = truthy non-array object with `.request`; family via string literal `type === 'people' | 'organizations'`; facet option = `{empty:boolean}` or `{exists:boolean}`; filter value-set = `{in:[...]}` or `{nin:[...]}`.

### Decisive source
```js
function isProfileSearchOption(data) {
    const arg = data;
    return Boolean(arg && (arg.empty === true || arg.empty === false || arg.exists === true || arg.exists === false));
}
function isISearchListData(data) {
    const arg = data;
    return Boolean(arg && !Array.isArray(arg) && arg.request);   // explicit array exclusion
}
function isIPeopleSearchListData(data) { return isISearchListData(data) && data.type === 'people'; }
function isProfileSearchOptionOrText(data) {
    return (0, strings_1.isNotEmptyString)(data) || isProfileSearchOption(data);
}
// common/guards.js
function isISearchDataInNin(data) {
    const arg = data;
    return (Boolean(arg) && typeof arg === 'object' &&
        (('in' in arg && Array.isArray(arg.in)) || ('nin' in arg && Array.isArray(arg.nin))));
}
```

**Flow:** a valid search list only has to be a non-array object carrying a `.request` — the request body itself is unpinned; the family discriminator is the lowercase string on `.type`. Facet filters come as either free text (non-empty string) or an option object whose single boolean flag chooses semantics: `empty:true` = match profiles where the field IS empty, `exists:true` = match profiles where the field is PRESENT. Value constraints are `in`/`nin` key-presence checks with `Array.isArray`.
**Invariant:** validation depth scales with persistence depth — search requests are transient (nothing persists), so the guard pins almost nothing (contrast entity aggregates, which whitelist dozens of props). The explicit `!Array.isArray(arg)` exists because the kernel's `isObject` accepts arrays; every payload guard must re-exclude them where shape matters.
**Probe:** deterministic node-require:
```bash
node -e "const g=require('$REFERENCE_ROOT/lh-basis/core/public-methods/shared-types/profilesSearch/guards.js');const c=require('$REFERENCE_ROOT/lh-basis/core/public-methods/shared-types/common/guards.js');console.log(g.isISearchListData({request:{}}),g.isISearchListData([1,2]),g.isIPeopleSearchListData({request:{},type:'people'}),g.isIOrganizationsSearchListData({request:{},type:'people'}),g.isProfileSearchOption({empty:false}),g.isProfileSearchOption({exists:1}),g.isProfileSearchOptionOrText('query'),c.isISearchDataInNin({in:[1]}),c.isISearchDataInNin({nin:'x'}))"
```
→ expect `true false true false true false true true false` (strict boolean flags — `exists:1` fails; `nin` must be an array).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "profiles search list data guard", file_pattern: "*profilesSearch*", limit: 10 });
```
Observed pass 3: returns all five guards (guards.js 11–27).

## Verdict
Adopt: minimal transient-payload guards with explicit array exclusion, literal-string family discriminators, and the empty/exists facet duality for "negative" filters. Adapt option names to your host. Omit the erased request-body schema (type-only shell). Cross-reference: chat-message-external-identifiers states the persistence-depth law this capsule confirms from the transient side.
