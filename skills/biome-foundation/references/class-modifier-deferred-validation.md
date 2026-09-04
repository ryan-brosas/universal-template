<!-- capsule-v2 -->
# Deferred modifier-list completion — how do you validate context-sensitive keywords (static/private/get) only after you know what kind of member they belong to?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Every JS class modifier word can also be a legal member name (`class A { static() {} }`) and the member's final node kind isn't known until after its body parses — so when can modifier legality actually be checked?

## ClassMemberModifiers: parse-all-now, validate-later
**Path/Symbol:** `crates/biome_js_parser/src/syntax/class.rs:parse_class_member_modifiers` (:1779-1799), `is_nth_at_modifier` (:1722-1753), `ClassMemberModifiers::validate_and_complete` (:2139-2183), `check_class_member_modifier` (:2263-2689), `parse_class_member` (:526-602).
**Signature:** `fn parse_class_member_modifiers(p: &mut JsParser, constructor_parameter: bool) -> ClassMemberModifiers` (returns a `#[must_use]` guard with a `DebugDropBomb`); `fn validate_and_complete(self, p, member_kind) -> bool`.
**Data Shape:** `modifiers: SmallVec<[ClassMemberModifier; 4]>` ({kind, start, length}), `flags: ModifierFlags` (u16 bitflags incl. synthesized `PRIVATE_NAME` set later by `set_private_member_name`), `list_marker: CompletedMarker` completed as `JS_BOGUS` at parse time.

### Decisive source
```rust
// at parse time the list kind is unknown — complete as BOGUS, re-kind later:
let list = list.complete(p, JS_BOGUS);
ClassMemberModifiers::new(modifiers, list, flags)
// ...
let modifiers_valid = modifiers.validate_and_complete(p, member.kind(p));
if !valid || !modifiers_valid { member.change_to_bogus(p); }

// inside validate_and_complete:
let list_kind = match member_kind {
    JS_PROPERTY_CLASS_MEMBER => JS_PROPERTY_MODIFIER_LIST,
    JS_GETTER_CLASS_MEMBER | JS_SETTER_CLASS_MEMBER | JS_METHOD_CLASS_MEMBER => JS_METHOD_MODIFIER_LIST,
    TS_PROPERTY_PARAMETER => TS_PROPERTY_PARAMETER_MODIFIER_LIST,
    JS_BOGUS_MEMBER | JS_STATIC_INITIALIZATION_BLOCK_CLASS_MEMBER => {
        self.list_marker.undo_completion(p).abandon(p); // no right list exists — remove it
        return false;
    }
    t => panic!("Unknown member kind {t:?}"),
};
self.list_marker.change_kind(p, list_kind);
```

**Flow:** greedily consume all modifier-looking tokens (a token counts as a modifier only if followed by a member name/`*`/another modifier — `static` alone stays a name) → parse the member body → complete the member → dispatch on its *final* kind to pick the modifier-list kind, then walk the ordered list with a `preceding_modifiers` bitflag accumulator emitting already-seen/must-precede/cannot-combine diagnostics.
**Invariant:** Validation is *post-hoc and order-aware*: precedence rules ("accessibility must precede static") are comparisons against flags of earlier tokens, while combination rules ("abstract cannot pair with private-name") compare against the full set. The drop bomb forces every path to either complete or abandon the list — including recovery paths where the member itself failed (`Absent => { debug_assert!(!flags.contains(ALL_MODIFIERS_EXCEPT_DECORATOR)); modifiers.abandon(p) }`). Static-init blocks reject any modifier by completing the list against their own kind (:962-974).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_class_modifier_precedence.ts` (pins `readonly private a`, `override protected base1`, `accessor static d`) and `error/ts_class_invalid_modifier_combinations.ts` (`private protected public c`, `abstract #j`, `declare accessor p`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ClassMemberModifiers validate_and_complete ModifierFlags", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves both functions with matching ranges (:1779-1799, :2139-2183).

## Verdict
Adopt deferred validation for any grammar where leading tokens are ambiguous between modifiers and names until the production completes; adapt flag sets; omit the constructor-parameter variant if the host language lacks parameter properties. Coverage caveat: full-mode index, metadata_match.
