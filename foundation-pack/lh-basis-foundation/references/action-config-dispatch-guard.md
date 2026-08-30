<!-- capsule-v2 -->
# Action config dispatch guard — How does ONE validator cover the config of EVERY action type without a per-type validator fleet?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** when dozens of action types share one config record, what is validated universally and what is deferred?

## Any-type config = enum membership + common shape + two explicit escape hatches
**Path/Symbol:** `core/public-methods/models/actions/ActionConfig/guards.js` — `isAnyActionConfig` (10–28); supports: `../ActionType/guards.js:isActionType` (= `ACTION_TYPES.includes(arg)`), `../TargetPlatform/guards.js:isTargetPlatform`.
**Signature:** `isAnyActionConfig(value): boolean`.
**Data Shape:** DB item + string-prop `actionType` that must be a member of ACTION_TYPES + 6 whitelisted props (`actionSettings`, `coolDown`, `maxActionResultsPerIteration`, `isDraft`, `autoTags`, `overridePlatform`) where `actionSettings` is **null-or-object** and `overridePlatform` is **valid-platform-or-null**.

### Decisive source
```js
function isAnyActionConfig(value) {
    return (isIDBItem(value) &&
        objectHasStringProperties(value, ['actionType']) &&
        isActionType(value.actionType) &&                    // universal dispatch key
        objectHasProperties(value, [
            'actionSettings', 'coolDown', 'maxActionResultsPerIteration',
            'isDraft', 'autoTags', 'overridePlatform',
        ]) &&
        (value.actionSettings === null || isObject(value.actionSettings)) &&   // settings may be DEFERRED (null)
        typeof value.coolDown === 'number' &&
        typeof value.maxActionResultsPerIteration === 'number' &&
        typeof value.isDraft === 'boolean' &&
        isObject(value.autoTags) &&
        (isTargetPlatform(value.overridePlatform) || value.overridePlatform === null));  // null = inherit
}
```

**Flow:** dbItem -> dispatch-key check (string prop whose value must be a known action type; membership via array `.includes`, so the constants list IS the registry) -> common-settings whitelist -> per-field primitive checks with exactly two tri-state slots: `actionSettings` null-or-object (per-action payload not yet materialized) and `overridePlatform` platform-or-null (null meaning "inherit campaign/default platform", distinct from any platform value).
**Invariant:** there is no per-type config validator in this kernel — type-specific structure lives behind the nullable `actionSettings` slot, so the shared guard can never reject a valid type for having "unknown extra fields" (whitelists here assert minimum presence). Null must stay distinguishable from undefined-style absence at both escape hatches.
**Probe:** `node -e`: config fixture `{id:1, actionType:'MessageToPerson', actionSettings:{}, coolDown:60, maxActionResultsPerIteration:10, isDraft:false, autoTags:{}, overridePlatform:null}` → `true` (actionType value must be an actual ACTION_TYPES member, e.g. 'MessageToPerson', 'InvitePerson', 'OrganizationsExtractor' — 34 values in ActionType/constants.js); `actionType:'no-such-type'` → `false`; `actionSettings:{}` vs `null` both pass; `overridePlatform:'other'` → `false`; `coolDown:'60'` → `false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "lh-basis", qualified_name: "lh-basis.core.public-methods.models.actions.ActionConfig.guards.isAnyActionConfig" });
```

## Verdict
Adopt single-guard-per-any-type config validation when types share a record shape: validate the dispatch key against the registry, keep type-specific payloads in an explicitly nullable slot, and give override knobs an explicit inherit-null. Adapt ACTION_TYPES vocabulary and setting names. Omit LinkedIn action taxonomy. Coverage: no_recorded_issue ×3 cited paths @ gen 2026-08-23T00:11:49Z; probe executed against shipped dist module (no test runner in ingest — standing block).
