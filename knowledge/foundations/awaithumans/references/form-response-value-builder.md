<!-- capsule-v2 -->
# Form Response Value Builder — how does a dynamic form submit wire-safe JSON to a strict Pydantic model?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Renderer state keeps blank optionals as `null`, but `field: str = ""` rejects None — where do you translate, and what stays?

## Omit-null-on-optional recursively; keep required nulls loudly
**Path/Symbol:** `packages/dashboard/components/form-renderer/build-response-value.ts:buildResponseValue` (:46–51) → `cleanLevel` (:53–124) / `cleanTableRow` (:126–137). Direct test: `build-response-value.test.ts`. Companion contracts: schema-form-inference.md, form-field-registry.md, complex-forms-capability-law.md.
**Signature:** `buildResponseValue(form: FormDefinition, value: FormValue): FormValue` — pure walk of definition × value together.
**Data Shape:** In: renderer state keyed by field name (blank plain-inputs initialized to `null`). Out: JSON body for `POST /api/tasks/{id}/complete` with non-required null/undefined keys OMITTED, required nulls KEPT, `""` and `[]` preserved verbatim.

### Decisive source
```ts
// The core rule: drop null on non-required fields so Pydantic
// defaults apply server-side. Required fields keep null so
// server-side validation can flag the violation explicitly.
if (v == null && !f.required) continue;

// section_collapse flattens — children's names live at the same
// level as the parent in `value`, matching the renderer's walk().
if (f.kind === "section_collapse") { Object.assign(out, cleanLevel(f.fields, value)); continue; }
if (f.kind === "subform")           out[f.name] = rows.map(r => cleanLevel(f.fields, r ?? {}));
if (f.kind === "table")             out[f.name] = rows.map(r => cleanTableRow(f.columns, r ?? {}));
if (f.kind === "object_group")      out[f.name] = cleanLevel(f.fields, sub);
if (f.kind === "repeatable_group")  out[f.name] = rows.map(r => cleanLevel(f.item_fields, r ?? {}));

// NON_INPUT_KINDS (display_text/image/video/pdf_viewer/html/
// section/divider) have layout names but never contribute values.
```

**Flow:** user submits → walk definition fields in order, skipping nameless/layout kinds → flatten section_collapse children into the parent level → for every value-bearing field apply the core rule (`v == null && !f.required` ⇒ omit) → recurse per row into subform/table/object_group/repeatable_group so a blank optional column on row 3 gets identical treatment → post the cleaned object.
**Invariant:** omission is keyed on BOTH null-equality (`== null` catches undefined too) AND not-required; required nulls survive so the server names the violation instead of the client silently hiding it. `""` is a meaningful answer distinct from untouched-null, and empty arrays are valid completions — neither is dropped. Recursion follows each composite kind's own row shape (`fields` vs `columns` vs `item_fields`). File stays `.ts` (no JSX) so vitest can unit-test it headlessly.
**Probe:** `build-response-value.test.ts` (:74–79 drops null optional; :81–89 keeps REQUIRED null pair; :91–97 preserves ""; :99–104 preserves []; :106–109 drops undefined like null; :111+ flattens section_collapse). Deterministic source probe (vitest runner blocked): `grep -cn 'cleanLevel' packages/dashboard/components/form-renderer/build-response-value.ts` → 6 occurrences (def + 4 recursions + export call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "buildResponseValue cleanLevel omit null optional pydantic", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-sided translation law: client omits exactly what Pydantic would default, keeps exactly what Pydantic must reject loudly. Adapt the composite-kind list to your primitive registry. Omit any server-side tolerance for null-on-non-Optional — the whole point is that the wire never carries it.
