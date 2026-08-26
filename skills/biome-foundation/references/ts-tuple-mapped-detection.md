<!-- capsule-v2 -->
# Tuple element matrix + mapped-type detection — how do named/optional/rest tuple elements coexist, and how is `{ [K in keyof T]: … }` told apart from a plain object type before parsing?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What lookahead distinguishes the four tuple element shapes, and what bounded scan decides mapped-vs-object type at `{`?

## TsTupleTypeElementList + is_at_start_of_mapped_type
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:TsTupleTypeElementList` (:1465-1557, predicate `is_at_named_tuple_type_element` :1548-1557), `is_at_start_of_mapped_type` (:1041-1059), `parse_ts_mapped_type` (:1080-1100).
**Signature:** `fn is_at_named_tuple_type_element(p: &mut JsParser) -> bool`; `struct TsTupleTypeElementList(TypeContext)` — `ParseSeparatedList` with trailing separators allowed and bogus recovery on `{']', '...', ident, '[', '{', void, null}`.
**Data Shape:** Tuple elements: `TS_NAMED_TUPLE_TYPE_ELEMENT` (`...name?: T`), `TS_REST_TUPLE_TYPE_ELEMENT` (`...T`), `TS_OPTIONAL_TUPLE_TYPE_ELEMENT` (`T?`), bare `parse_ts_type`. Mapped type: `{ [+/-]readonly [K in U [as V]] [+/-]? : T ; }`.

### Decisive source
```rust
let offset = usize::from(p.at(T![...]));          // rest prefix shifts every probe
let is_colon = p.nth_at(offset + 1, T![:]);        // a:
let is_question_colon = p.nth_at(offset + 1, T![?]) && p.nth_at(offset + 2, T![:]); // a?:
is_nth_at_identifier_or_keyword(p, offset) && (is_colon || is_question_colon)
```
```rust
fn is_at_start_of_mapped_type(p: &mut JsParser) -> bool {
    if p.nth_at(1, T![+]) || p.nth_at(1, T![-]) { return p.nth_at(2, T![readonly]); }
    let mut offset = 1;
    if p.nth_at(offset, T![readonly]) { offset += 1; }   // optional readonly
    p.nth_at(offset, T!['['])
        && (is_nth_at_identifier(p, offset + 1) || p.nth(offset + 1).is_keyword())
        && p.nth_at(offset + 2, T![in])                   // [K in …
}
```

**Flow:** tuple parse: named-probe first (completing `…?:` combos), then rest, then optional-suffix via `precede`, else bare type; both-rest-and-optional completes then demotes to bogus ("A tuple member cannot be both optional and rest."). Mapped-vs-object: at `{` run the scan above — `+`/`-` require `readonly` next; otherwise skip an optional `readonly` and demand `[ ident|keyword in`.
**Invariant:** The named-element offset trick means `...a:` and `a?:` are recognized by ONE probe family. Mapped detection must tolerate keyword keys (`{ [in in X]: …}`) yet NOT treat index signatures `[a: number]` as mapped (the `in` requirement does it). Optional-mapping clauses parse AFTER the closing `]` — order: as-clause inside brackets, `?`-modifier outside.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_tuple_type.ts` (`[a: string, b: number, ...c: any[]]`, `[a?: string]`) / `error/ts_tuple_type_cannot_be_optional_and_rest.ts` and `ok/ts_mapped_type.ts` (+ `-readonly [P in keyof T]-?: …`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "mapped type is_at_start tuple named element optional rest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt offset-shifted probes and the pre-parse `{` classification scan; adapt kinds; omit recovery token spellings. Complements ts-type-member-dispatch.md (member level vs type level).
