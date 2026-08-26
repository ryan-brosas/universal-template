<!-- capsule-v2 -->
# External identifier type algebra — How do I validate and canonicalize a person identity that may arrive as 10 different wire types?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** a porter must know which identifier shapes are legal and how to reduce them to one comparable key without a schema validator.

## Person identity namespace-module (`IPersonExternalIdentifier`)
**Path/Symbol:** `core/public-methods/models/people/PersonExternalIdentifier/IPersonExternalIdentifier.js` — nested namespaces `Type.Member|Hash|Public|Avatar`, `TypeGroup`, `ExternalIdWithType`, `UniqueId` (file lines 13–287; `ExternalIdWithType.is` 148–172; `isValidExternalIdentifierData` 199–229).
**Signature:** `ExternalIdWithType.is(data: {externalId: string, type: string}) => boolean`; `isValidExternalIdentifierData(data) => boolean`; `UniqueId.fromExternalIdWithTypeOrTypeGroup(data | data[]) => string | string[]`.
**Data Shape:** 10 wire types (`enums.js`): member-id, sn-member-id, r-member-id, t-member-id, li-hash-id, sn-hash-id, r-hash-id, t-hash-id, public-id, full-name-avatar-id -> 4 groups **member | hash | public | avatar** (`TypeGroup.is`: `['member','public','hash','avatar'].includes(arg)`). sn-/r-/t- variants additionally require `authType`+`authToken` strings. Redundant fields enforced: member data needs `memberId === Number(externalId)`; hash data needs `hash === externalId`.

### Decisive source
```js
function isValidExternalIdentifierData(data) {
    if (objectHasStringProperties(data, ['type'])) {
        switch (data.type) {
            case 'member-id':      return isCommonMemberExternalIdentifierData(data);
            case 'sn-member-id': case 'r-member-id': case 't-member-id':
                return isCommonMemberExternalIdentifierData(data) &&
                       objectHasNotEmptyStringProperties(data, ['authType', 'authToken']);
            case 'li-hash-id': case 't-hash-id': return isCommonHashExternalIdentifierData(data);
            case 'sn-hash-id': case 'r-hash-id':
                return isCommonHashExternalIdentifierData(data) &&
                       objectHasStringProperties(data, ['authType', 'authToken']); // NOT notEmpty!
            case 'full-name-avatar-id': return isAvatarExternalIdentifierData(data);
        }
    }
    return false;
}
// canonical dedup key
return `${typeGroup}:${data.externalId}`;   // UniqueId.fromExternalIdWithTypeOrTypeGroup
```

**Flow:** object guard (`objectHasNotEmptyStringProperties(data,['externalId','type'])`) -> map type to group via `TypeGroup.fromType` -> switch on group to the per-group validator (`Member.isValidMemberId(Number(externalId))` = positive number; hash = shape check; public/avatar = non-empty string). Unknown group throws inside a try/catch that returns `false`. Auth-gated serialization (`utils.convertPersonExternalIdentifierToString`) emits `${externalId},${authToken},${authType}` for `Type.WithComma`.
**Invariant:** group dispatch never trusts the type string alone — the externalId value itself must satisfy the group's validator; denormalized mirror fields (memberId/hash) must equal their source field or validation fails.
**Probe:** `node -e "const m=require('<root>/core/public-methods/models/people/PersonExternalIdentifier/index.js'); const E=m.guards?0:require('<root>/core/public-methods/models/people/PersonExternalIdentifier/IPersonExternalIdentifier.js').IPersonExternalIdentifier.ExternalIdWithType; console.log(E.is({externalId:'123',type:'member-id'}), E.is({externalId:'ACoAAA',type:'li-hash-id'}))"` → expect `true false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", qn_pattern: ".*PersonExternalIdentifier.*", format: "json", limit: 40 });
```

## Verdict
Adopt the group-taxonomy + dispatch-validation pattern and the `${group}:${externalId}` dedup key for any multi-surface identity store. Adapt type strings/prefix lists to your host. Omit LinkedIn-specific prefix sets and PAS fields if your product has no PAS; keep citations-only (proprietary source). Note the deliberate asymmetry: sn/r hash ids accept empty-string auth fields while member ids require non-empty — preserve or consciously fix it.