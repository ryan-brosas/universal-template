<!-- capsule-v2 -->
# Person type→group projection — How do you map identifier TYPE SETS onto groups with a fail-closed entry over fail-open inner steps?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** given one type string OR an array of type strings, how does the kernel project them onto group names (`member|hash|public|avatar`) — and exactly where does it throw versus pass through?

## Public throwing `fromType` over private fall-through `fromSingleType`
**Path/Symbol:** `core/public-methods/models/people/PersonExternalIdentifier/IPersonExternalIdentifier.js` — `TypeGroup.isTupleOfTypeOrTypeGroup` (109–111), `TypeGroup.fromSingleType` (112–126), `TypeGroup.fromType` (127–135), alias `Type.toGroup = TypeGroup.fromType` (143); group membership `TypeGroup.is` (137–139).
**Signature:** `fromType(types: string | string[]): string | string[]` — THROWS on invalid argument; `isTupleOfTypeOrTypeGroup(arg): boolean`; `fromSingleType(type): string` is **module-private at runtime**.
**Data Shape:** input = one wire-type string (e.g. `'t-hash-id'`) or non-empty array of wire-type/group strings; output mirrors input arity — one group name per element; unknown elements inside a valid-shape tuple would pass through `fromSingleType` unchanged, but the tuple gate rejects them first.

### Decisive source
```js
function isTupleOfTypeOrTypeGroup(arg) {
    return Array.isArray(arg) && arg.length > 0 && !arg.find((item) => !Type.is(item) && !TypeGroup.is(item));
}
function fromSingleType(type) {
    if (Type.Member.is(type)) return 'member';
    if (Type.Hash.is(type))   return 'hash';
    if (Type.Public.is(type)) return 'public';
    if (Type.Avatar.is(type)) return 'avatar';
    return type;                                    // private fall-through, unreachable via public API
}
function fromType(types) {
    if (isTupleOfTypeOrTypeGroup(types)) return types.map((type) => fromSingleType(type));
    if (Type.is(types) || TypeGroup.is(types)) return fromSingleType(types);
    throw new Error(`Invalid types argument: ${types}`);   // fail-closed ENTRY
}
```
Runtime probe finding: `typeof M.TypeGroup.fromSingleType === 'undefined'` and same for `isTupleOfTypeOrTypeGroup` — neither is exported on the namespace; only `fromType` and `is` are public.

**Flow:** shape gate → either tuple branch (every element pre-validated as Type or TypeGroup, then mapped one-to-one) or singular branch (whole-string membership check) → otherwise THROW with the offending value interpolated. The inner `fromSingleType` ends in `return type;` (fail-open), but no caller can reach that line with an unvalidated value because both branches of `fromType` gate first — and `Unique.fromExternalIdWithTypeOrTypeGroup` reaches groups only through `Type.toGroup(data.type)` after the payload already passed `isValidExternalIdentifierData`.
**Invariant:** the PUBLIC contract is fail-closed (throws `Invalid types argument`), yet the code keeps a fail-open step buried inside as a deliberate trap: anyone calling the private mapper directly, or adding a new public caller that skips the gates, silently emits identity-mapped pseudo-groups like `'mystery'`. Porters must preserve gate-before-map ordering; the alias `Type.toGroup === TypeGroup.fromType` (probe-verified `true`) means both names share the throwing behavior.
**Probe:** executed against dist module:
```bash
node -e "const M=require('<root>/.../IPersonExternalIdentifier.js').IPersonExternalIdentifier;
console.log(JSON.stringify(M.TypeGroup.fromType(['member-id','public-id'])), M.TypeGroup.fromType('li-hash-id'), M.Type.toGroup===M.TypeGroup.fromType);
try { M.TypeGroup.fromType('mystery') } catch(e){ console.log('threw:'+e.message) }
try { M.TypeGroup.fromType(['member-id','mystery']) } catch(e){ console.log('threw:'+e.message) }"
```
→ observed `["member","public"] | hash | true | threw:Invalid types argument: mystery | threw:Invalid types argument: member-id,mystery`.
**Retrieve (executed pass 5):**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", name_pattern: ".*(fromSingleType|isTupleOfTypeOrTypeGroup|fromExternalIdWithTypeOrTypeGroup)", fields: ["lines"] });
```
→ observed 4 rows incl. `IPersonExternalIdentifier.fromSingleType 112-126`, `isTupleOfTypeOrTypeGroup 109-111`.

## Verdict
Adopt "validate the argument shape at the single public entry, then map" for any taxonomy projection exposed to callers; keep inner mappers total but PRIVATE so the fail-open branch is dead code behind the gate. Adapt group vocabularies freely; keep array-in/array-out arity mirroring for batch UIs. Omit LinkedIn type lists. Contrast (do not copy blindly): the org twin's `TypeGroup.fromType` has NO throwing gate — see organization-unique-id-normalization. Coverage: file fully indexed (`no_recorded_issue` @ gen 2026-08-23T00:11:49Z); probes executed against shipped dist module (no test runner in ingest — standing block).

Cross-references: external-identifier-type-algebra (the value-side dispatch this type-set projection complements), organization-unique-id-normalization (fail-open twin without the gate).
