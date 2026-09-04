<!-- capsule-v2 -->
# Ambient-read promotion ladder — `typeof X`, qualified names, and import-shadow traps

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does a resolver distinguish "read a value", "read a type", and "read an imported VALUE as a type" — including when a local shadows the imported name?

## Reference::{Read, AmbientRead} + parent-kind dispatch + pop-time demotion
**Path/Symbol:** `crates/biome_js_semantic/src/events.rs` — `enum Reference{Export, Read, AmbientRead, Write}` (:222-273), classification in `enter_identifier_reference` (:812-929): JS_EXPORT_NAMED_(SHORTHAND_)SPECIFIER → dual Export pair; grandparent JS_EXPORT_DEFAULT_EXPRESSION_CLAUSE|TS_EXPORT_ASSIGNMENT_CLAUSE → dual Export; ancestor-scan skipping TS_QUALIFIED_NAME (:879-895) — TS_REFERENCE_TYPE+qualified ⇒ AmbientRead(Value), TS_REFERENCE_TYPE bare ⇒ Read(Type), TS_IMPORT_TYPE_QUALIFIER ignored entirely, TS_TYPEOF_TYPE ⇒ AmbientRead(Value); resolution ladder in `resolve_references_in_scope` namespace-import rejection (:1209-1226) and ambient-promotion arm (:1227-1242); dual-scope handler `resolve_references_in_dual_scope` (:1277-1325, AmbientRead-of-imported-value resolves with ScopeId(0)).
**Signature:** `Reference::is_ambient_read()` gates the promotion branch; `BindingInfo.is_imported()` matches import-specifier syntax kinds incl. bogus named specifier.
**Data Shape:** Promotion = re-queueing `Reference::AmbientRead(range)` into the PARENT scope's references under the SAME name — resolution simply retries one level out.

### Decisive source
```rust
// A value binding can shadow a type-only import with the same name.
// Promote ambient reads so the parent scope can resolve the type binding.
// Only do this when the dual binding is imported; otherwise `typeof a`
// should keep resolving to the local value binding (#9519).
if reference.is_ambient_read()
    && !info.is_imported()
    && self.bindings.get(&name.clone().dual()).is_some_and(|dual| dual.is_imported())
    && let Some(parent) = self.scopes.last_mut()
{
    parent.references.entry(name.clone()).or_default().push(Reference::AmbientRead(reference.range()));
    continue;
}
```

**Flow:** Sighting classifies by SYNTAX context (parent/grandparent/ancestor kinds). Resolution tries: exact name → dual name → (ambient-only) promote-to-parent → UnresolvedReference. Two special rejections guard correctness: reading a namespace import AS a type emits BOTH UnresolvedReference AND Read (deliberate double event so noUndeclaredVariables and noUnusedImports each stay consistent — TODO comment :1218-1221); `this` is skipped in typeof and JSX positions.
**Invariant:** Ambient reads are the ONLY references allowed to escape a shadowing local — plain Reads die at the shadow (#9519 regression). Export events are emitted regardless of hoisting direction but still carry Read-vs-HoistedRead alongside. The dual lookup means a Value miss can still resolve as a Type read — porters who drop `dual()` lose all `let x: X`-style resolutions.
**Probe:** `src/tests/references.rs::ok_unresolved_reference_arguments` (arguments unresolved everywhere), `tests/functions.rs::ok_function_inside_module` (`f/*?*/` inside declare-module), `ok_import_used_in_jsx`; #9519 comment-pinned above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "AmbientRead TS_TYPEOF_TYPE TS_REFERENCE_TYPE is_imported promote parent references", limit: 10 });
```

## Verdict
Adopt the sighting-classifies/resolution-retries split; adapt the parent-kind table to your type grammar; keep the double-event quirk ONLY if you also ship the two rules that consume it separately.
