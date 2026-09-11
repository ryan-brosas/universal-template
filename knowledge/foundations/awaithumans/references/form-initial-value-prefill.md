<!-- capsule-v2 -->
# Form Initial-Value + Prefill — how do you seed dynamic-form state from server defaults plus untrusted prefill without display fields or type-mismatched values leaking into the response?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What per-kind default ladder and prefill acceptance rule make a form's starting state safe when the seed data comes from a third-party extraction?

## Derived state, typed seeds, recursive row descent
**Path/Symbol:** `packages/dashboard/components/form-renderer/initial-value.ts` — `initialValueFor` (:20–27), `NON_INPUT_KINDS` (:35–43), `walk` (:45–156). Pure module by design ("no JSX, no React — so vitest can import this directly").
**Signature:** `initialValueFor(form: FormDefinition, prefill?: Record<string, unknown> | null): FormValue`.
**Data Shape:** `FormValue` = name→value tree; defaults per kind — switch `boolean|null`, single_select `string|null`, multi_select/picture_choice/table/subform `[]`, slider `(min+max)/2`, star_rating `0`, opinion_scale/date/datetime/time `null`, ranking = option order (identity default), plain inputs `null`.

### Decisive source
```ts
if (!f.name) continue;
if (NON_INPUT_KINDS.has(f.kind)) continue;   // display primitives never enter state:
                                             // else {"intro": null} pollutes responses
const seeded = prefill !== null && f.name in prefill ? prefill[f.name] : undefined;
case "switch":
    out[f.name] = typeof seeded === "boolean" ? seeded : (f.default ?? null);
case "slider":
    out[f.name] = typeof seeded === "number" ? seeded : (f.default ?? (f.min + f.max) / 2);
```

**Flow:** renderer mount → `initialValueFor(form)` builds starting state → each field's seed is accepted ONLY when its runtime type matches the kind's expectation (`typeof === "boolean"`/`"string"`/`"number"`/`Array.isArray`) — a mismatched seed falls back to the kind default, never stored raw → `section_collapse` children flatten into the parent scope (its own name never appears) → `object_group` descends into a nested prefill sub-object, children falling back to their own defaults if the seed isn't a plain object → `repeatable_group` maps seed rows and recurses `walk(f.item_fields, rowOut, row)` PER ROW so a partially-filled extraction row still receives per-field defaults for missing keys → submission later runs the inverse discipline in `form-response-value-builder.md`.
**Invariant:** untrusted prefill can fill values but cannot inject SHAPES: wrong-typed keys degrade to defaults, display-only kinds stay out of the payload, and every recursion preserves the "missing key ⇒ field default" rule at every nesting depth.
**Probe:** `packages/dashboard/components/form-renderer/initial-value.test.ts` (`form`:23–25, `shortText`:27–41, `switchField`:43–54 boolean-vs-default branches, `objectGroup`:56–65 nested descent, `repeatableGroup`:67–78 per-row defaults). Vitest runner blocked this lane (no node_modules) — deterministic source probes executed instead: grep confirms `NON_INPUT_KINDS` defined :35 with exactly one membership check (:52), and the slider midpoint expression `(f.min + f.max) / 2` at :84; embed page consumes it as `initialValueFor(fetched.form_definition)` on task load (app/embed/page.tsx:79–81).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "initialValueFor walk NON_INPUT_KINDS prefill", limit: 8 });
```
Live rank −30.01 `initialValueFor` :20–27 and −28.46 `walk` :45–156, line-exact; test symbols pinned at :43–54/:56–65/:67–78.

## Verdict
Adopt the derived-state approach and the typed-seed acceptance ladder verbatim whenever form seeds cross a trust boundary. Adapt the kind list and midpoint default to your primitive set (keep ranking=option-order: it makes the identity permutation the zero-effort answer). Omit NON_INPUT_KINDS only if your response contract tolerates null-pollution from named display fields — audits won't.
