<!-- capsule-v2 -->
# JsDeclarationKind ladder — one enum classifying every JS/TS binding family

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does downstream code learn WHAT KIND of declaration produced a binding (and therefore its hoisting/type/value behavior) from just the binding node?

## 13-kind enum + ancestor-walk classifier + three predicates
**Path/Symbol:** `crates/biome_js_semantic/src/semantic_model/binding.rs` — `enum JsDeclarationKind` (:17-86: Class, Enum, Function, Generic, HoistedValue, Import, ImportType, Interface, Module, Namespace, Type, Unknown(default), Using, Value), `declares_namespace/declares_type/declares_value` (:88-126), `from_node(node)` ancestor walk (:129-174); extractor-side per-declaration match in `events.rs:enter_identifier_binding` (:552-781).
**Signature:** `JsDeclarationKind::from_node(&JsSyntaxNode) -> Self` walks ancestors to the first `AnyJsDeclaration`/`JsImport`/`TsTypeParameter`; variable kind maps Const|Let→Value, Using→Using, Var→HoistedValue, Err→Unknown; `namespace` vs `module` keyword decided by `module_or_namespace().text_trimmed()`.
**Data Shape:** Kind is carried through `SemanticEvent::DeclarationFound.declaration_kind` into `SemanticModelBindingData.declaration_kind` — queryable later as `binding.declaration_kind()`.

### Decisive source
```rust
AnyJsDeclaration::JsVariableDeclaration(decl) => match decl.variable_kind() {
    Ok(JsVariableKind::Const | JsVariableKind::Let) => Self::Value,
    Ok(JsVariableKind::Using) => Self::Using,
    Ok(JsVariableKind::Var)     => Self::HoistedValue,
    Err(_)                      => Self::Unknown,
},
if let Some(import) = JsImport::cast(ancestor) {
    return match import.import_clause() {
        Ok(clause) if clause.type_token().is_some() => Self::ImportType,
        _ => Self::Import,
    };
}
```

**Flow:** The extractor's giant match assigns kinds WITH hoist targets in one place (var-pattern-in-var → skip-0 HoistedValue; function decls → Function w/ strict-dependent skip-1; export-default function → HoistedValue; enum members → Enum with quoted-name normalization via `inner_string_text`; TsInferType → deferred, returned EARLY before any binding push because its scope doesn't exist yet — see infer-fallback-scope-flush.md). Predicates then derive behavior: `declares_type` includes Unknown deliberately (a bogus declaration still occupies the type slot so references don't mis-promote).
**Invariant:** `Unknown` participates in BOTH declares_type AND declares_value — porters who make Unknown declare nothing break bogus-node resolution ordering. Bogus-named bindings take a separate path (`declaration()` Err ⇒ info keyed off node.kind(), pushed as Value, never exported :784-791). The kind is assigned ONCE at extraction; the model never re-derives it from syntax — single source of truth.
**Probe:** `src/tests/references.rs::ok_function_parameter_array_with_name_conflict` (pattern-in-param naming), `tests/scopes.rs::ok_scope_overloaded_functions`; `format.rs` snapshot shows rendered kinds end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "JsDeclarationKind from_node declares_type declares_value HoistedValue Using", limit: 10 });
```

## Verdict
Adopt the kind enum + predicate derivation shape for any binding taxonomy; adapt kind set to your grammar's surface; omit from_node's walk if your extractor already carries the kind at the binding site (biome needs both because builder-side re-entry happens from bare nodes).
