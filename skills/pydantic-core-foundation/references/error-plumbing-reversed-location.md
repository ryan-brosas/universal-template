<!-- capsule-v2 -->
# Error plumbing — how do ValError/ValLineError/Location compose into a ValidationError with reversed locs?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** Why is location stored REVERSED and how must outer locations be attached during unwinding?

## Locations are push-onto-reversed-vec; every outer frame prepends by pushing; display reverses
**Path/Symbol:** `src/errors/line_error.rs` (whole file, 171L): `ValError::{LineErrors, InternalErr, Omit, UseDefault}`, ValLineError; `src/errors/location.rs` (whole file, 195L): LocItem/Location.
**Signature:** `with_outer_location(self, impl Into<LocItem>) -> Self` consumes-and-prefixes; `ValError::with_outer_location` maps over all lines (:86-97).
**Data Shape:** `LocItem::{S(String), I(i64)}`; `Location::{Empty, List(Vec<LocItem>)}` REVERSED; Display joins reversed items with "." quoting S-items containing dots (`{s}` backtick form :29).

### Decisive source
```rust
// line_error.rs — the whole reason for reversal:
/// location is stored reversed so it's quicker to add "outer" items as that's what we always do
pub fn with_outer_location(mut self, into_loc_item: impl Into<LocItem>) -> Self {
    self.location.with_outer(into_loc_item.into());  // Vec::push on the reversed vec
    self
}
// location.rs:
/// Note: location in List is stored in **REVERSE** so adding an "outer" item to location involves
/// pushing to the vec which is faster than inserting and shifting everything along.
```

**Flow:** Leaf validators create ValLineErrors with their OWN loc item (or Empty); as errors unwind, each container pushes its key/index/tag via with_outer_location — union choices use validator-name-or-label, model-fields uses lookup-path-aware apply_error_loc honoring loc_by_alias. At the top, SchemaValidator converts ValError → Python ValidationError via `ValidationError::from_val_error(py, title, input_type, ...)` (:484-494 mod.rs) carrying hide_input_in_errors/validation_error_cause flags; InternalErr bypasses line machinery entirely. Omit/UseDefault are CONTROL-FLOW variants — only legal to surface where a default/exclusion consumer exists (isinstance maps them to dedicated errors, :240-241).
**Invariant:** Never sort or dedupe LineErrors — order is choice/field iteration order and tests assert exact arrays. InputValue snapshot (Python obj or owned JsonValue) is taken AT ERROR CREATION, not at raise time.
**Probe:** `grep -n 'REVERSE' src/errors/location.rs` =2 hits (:87 comment, :96); direct tests: tests/test_errors.py green this pass (551 batch); recursion_loop payload test asserts full dict incl input object.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "ValLineError with_outer_location Location", limit: 5 });
// live rank-family: line_error/location symbols resolve line-exact
```

## Verdict
Adopt: reversed-storage + push-prefix pattern (or your language's deque-appendleft equivalent), four-variant ValError taxonomy with control-flow members consumed at defined sites, error-time input snapshots. Adapt LocItem to str|int union of your host. Omit serde Serialize impls unless you emit structured errors.
