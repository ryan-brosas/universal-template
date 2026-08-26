<!-- capsule-v2 -->
|# Declarative delay validation — how do I validate a bot's per-action {min,max} timing config so bad ranges die at load, not mid-campaign?

**Source:** lh-basis (Linked Helper) **NO LICENSE — learn-only: pattern recorded, zero code copied**; Codebase Memory `lh-basis-source` (root `…/core/local-source/dist/Source`). **Question:** when an automation product lets users tune humanized delays for every action, what validation contract guarantees each configured range is well-formed before the browser ever launches?

## MinMax nested range + cross-field max>=min custom validator
**Path/Symbol:** `ActionSettings/helpers/Delays.js` — `MinMax` class (`min`/`max`, both `IsNumber + Min(0)`), `TransformDelays(allowedKeys)` (whitelist-strip transform), `IsValidDelay(label)` composite decorator = `IsOptional + IsNotEmptyObject + ValidateNested + Type(()=>MinMax) + IsMaxNotLessThanMin(label)`; applied per action-key on the `Delays` class (`navigateToProfile`, `loadGroupMemberPage`, `clickOnMessageButton`, `switchSendMethod`, `typeMessage`, …); consumed by `validateActionSettings.js:validateActionSettings` (plainToClass → validateSync → error filtering).
**Signature:** `IsValidDelay(humanLabel: string): PropertyDecorator` — the label exists ONLY to be interpolated into the failure message: `"Delay settings for '<label>' are invalid: 'max' shouldn't be less than 'min'"`.
**Data Shape:** every delay is `{ min: number ≥ 0, max: number ≥ 0 }` with `max >= min`; unknown keys in the incoming object are DELETED before validation (`for k in value: if !allowed.includes(k) delete t[k]`) so typos fail as missing-required rather than silently passing.

### Decisive source (de-minified)
```ts
class MinMax {
  @IsNumber() @Min(0) min: number;
  @IsNumber() @Min(0) max: number;
}
function IsMaxNotLessThanMin(label) {   // CROSS-FIELD rule lives at the property,
  return registerDecorator({            // not inside the nested class
    validator: { validate(value, args) {
        const d = args.object[propertyName];
        return typeof d.min === 'number' && typeof d.max === 'number' && d.max >= d.min;
      },
      defaultMessage: () => `Delay settings for '${label}' are invalid:
                             'max' shouldn't be less than 'min'` }});
}
function IsValidDelay(label) {
  return compose(IsOptional(), IsNotEmptyObject(), ValidateNested(),
                 Type(() => MinMax), IsMaxNotLessThanMin(label));
}
// one line per automatable action:
@IsValidDelay("Navigate to profile")       navigateToProfile: Delays;
@IsValidDelay('Type message')              typeMessage: Delays;
```
**Flow:** raw settings JSON → whitelist-strip to known keys → plainToClass into decorated classes → sync validation → errors carry the human action label → caller refuses to start the campaign until clean.
**Invariant:** the cross-field constraint (`max >= min`) is validated where BOTH fields are visible (parent property via `args.object`), never inside `MinMax` itself where only one field loads at a time; every new action key MUST get its own `@IsValidDelay(<human label>)` line — validation coverage and action surface grow together; invalid config throws BEFORE any browser/session work (fail-fast at composition root).
**Probe:** no test suite ships in the extract — coverage caveat. Deterministic probe (anchored at `lh-basis/core/local-source/dist/ActionSettings/helpers`): `grep -o "IsValidDelay(\"[^\"]*\"" Delays.js | wc -l` counts decorated action keys (>20); `grep -c "shouldn't be less than" Delays.js` ⇒ 1 canonical message; graph anchor resolves under project `lh-basis-source` (Delays/validation symbols indexed).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "lh-basis-source", query: "Delays MinMax IsValidDelay validate", limit: 5 });`

## Verdict
Adopt: typed `{min,max}` delay objects with a cross-field max≥min validator whose error message names the human-readable action, whitelist-stripping of unknown keys pre-validation, and synchronous validation at startup. Adapt the mechanism freely (pydantic `model_validator`, zod `.refine`, or plain asserts) — the CONTRACT is portable, the class-validator machinery is not required; extend the same shape from delays to any bounded-numeric action setting (caps, retries). Omit nothing — but note this is the CONFIG-side twin of throttle-classification-ladder (runtime limits) and complements config-validation-ladder (file-level checks): file lint → schema validation → runtime throttles forms the full fail-fast ladder.
