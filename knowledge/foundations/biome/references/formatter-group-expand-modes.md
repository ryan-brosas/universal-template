<!-- capsule-v2 -->
# Group builder + expand_parent — how do should_expand, group_id and the ExpandParent element cooperate to force a group open?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** When a porter wraps content in `group(...)`, what three independent "force break" mechanisms exist and which one wins?

## Group emission with optional id + mode
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:2038-2096` (`group()`, `Group` struct, `with_group_id`, `should_expand`, `Format::fmt`), `builders.rs:2134-2145` (`expand_parent`).
**Signature:** `pub fn group<Context>(content: &impl Format<Context>) -> Group<'_, Context>`; `Group::with_group_id(Option<GroupId>) -> Self`; `Group::should_expand(bool) -> Self`.
**Data Shape:** `tag::Group::new().with_id(self.group_id).with_mode(mode)` where `mode ∈ {GroupMode::Flat (default), GroupMode::Expand}` — the builder struct is Copy and carries the decision into ONE tag.

### Decisive source
```rust
// builders.rs:2071-2085
impl<Context> Format<Context> for Group<'_, Context> {
    fn fmt(&self, f: &mut Formatter<Context>) -> FormatResult<()> {
        let mode = match self.should_expand {
            true => GroupMode::Expand,
            false => GroupMode::Flat,
        };
        f.write_element(FormatElement::Tag(StartGroup(
            tag::Group::new().with_id(self.group_id).with_mode(mode),
        )))?;
        Arguments::from(&self.content).fmt(f)?;
        f.write_element(FormatElement::Tag(EndGroup))
    }
}
// builders.rs:2134-2145 — expand_parent is a UNIT ELEMENT, not a group option
pub const fn expand_parent() -> ExpandParent { ExpandParent }

impl<Context> Format<Context> for ExpandParent {
    fn fmt(&self, f: &mut Formatter<Context>) -> FormatResult<()> {
        f.write_element(FormatElement::ExpandParent)
    }
}
```

**Flow:** `group(&content)` defaults Flat → `.should_expand(true)` bakes Expand INTO the StartGroup tag (used inside best_fitting variants that must never print flat) → `.with_group_id(Some(id))` makes the group addressable by name for remote conditionals → a child may instead emit the standalone `ExpandParent` element, forcing its enclosing (not necessarily direct) group to expand. Prettier parity: `expand_parent` == `break_parent` (doc :2132-2133).
**Invariant:** Three distinct mechanisms must NOT be conflated by a porter: (1) `should_expand(true)` = unconditional self-expansion recorded in the tag; (2) `group_id` = addressing only, changes nothing about this group's own mode; (3) `ExpandParent` = child→parent upward signal emitted as an inline element mid-content. `has no effect if used outside of a group or element that introduce implicit groups (fill element)` (:2098-2100).
**Probe:** `grep -c 'GroupMode::' crates/biome_formatter/src/builders.rs` → `2`; `grep -n 'with_mode(mode)' crates/biome_formatter/src/builders.rs` → `2079:`; `grep -c 'write_element(FormatElement::ExpandParent)' crates/biome_formatter/src/builders.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"Group should_expand with_group_id","limit":6,"detail":"ids"}'
```
Resolves `biome.crates.biome_formatter.src.builders.Group.*` line-exact (Struct 2047-2051, Methods 2054-2068, fmt 2072-2085).

## Verdict
Adopt the single-tag group model (id + mode travel together in StartGroup) and the separate ExpandParent unit element; adapt tag representation to host IR. Direct tests pin both flat and expanded outcomes: doc examples :2104-2129 (`expand_parent` forces `[...]` to split) and the best_fitting should_expand suite at macros.rs:243-301.
