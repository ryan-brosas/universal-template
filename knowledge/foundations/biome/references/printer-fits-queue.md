<!-- capsule-v2 -->
# Printer queue + FitsQueue — how does the formatter printer decide a group fits on a line?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the printer's `FitsQueue`/`PrintQueue` implement the "fits" probe that drives BestFitting/line-breaking, and how are tokens measured?

## Printer queues
**Path/Symbol:** `crates/biome_formatter/src/printer/queue.rs` (383L): `PrintQueue` (:37-), `FitsQueue` (:163-166), `PrintCall`/`FitsCall`; consumed by `crates/biome_formatter/src/printer/mod.rs:Printer` (:2529L, `fits_element`/`print_element`).
**Signature:** `struct FitsQueue { fits: Vec<FitsCall>, check_stack: Vec<FitsElement> }`; `struct PrintQueue { print: Vec<PrintCall> }`.
**Data Shape:** Two explicit stacks. `FitsCall` carries a `FitsMode` (OnlyIfBreaks / SkipIfFitsOnSingleLine) and the remaining print-width budget; `FitsElement` is the element being probed. `PrintCall` wraps a `FormatElement` + `Document` + mode.

### Decisive source
```rust
// queue.rs — the fits probe is a bounded lookahead that must NOT mutate the real print state
pub struct FitsQueue {
    fits: Vec<FitsCall>,
    check_stack: Vec<FitsElement>,
}
```
The printer runs the fits probe by draining `FitsQueue` against a width budget; if any element exceeds the remaining width (or a hard line break / non-fitting `BestFitting` variant is hit), the group is judged "doesn't fit" and the printer switches to the expanded/indented layout.

**Flow:** `print_element` pushes `PrintCall`s onto `PrintQueue` and pops them in reverse for correct nesting → when it reaches a group/BestFitting it forks a `FitsQueue` probe that walks the same elements WITHOUT committing output → the probe returns fit/no-fit → the group is printed flat (fits) or expanded (doesn't) → `PrintQueue` continues with the chosen branch.
**Invariant:** The fits probe must be side-effect free w.r.t. the real print state — it shares the token/text measurement but never advances the actual output cursor. Width accounting must match the real printer exactly (same indent, same line-ending normalization), or flat/expanded decisions drift from the rendered width. `FitsMode::OnlyIfBreaks` only counts content that would break.
**Probe:** `crates/biome_formatter/src/printer/mod.rs::tests::it_prints_a_group_on_a_single_line_if_it_fits` (:1665) + `it_breaks_a_group_if_a_string_contains_a_newline` (:1787) — direct #[test]s.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Printer queue fits best_fitting", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `printer.queue.FitsQueue` (:163-166).

## Verdict
Adopt a side-effect-free fits probe backed by a dedicated queue as the core of any best-fit printer; adapt width accounting to your line-ending/indent model; omit Biome's specific `BestFitting`/`Fill` variants (already covered by `formatter-ir.md`). Pairs with the existing formatter-IR capsule — this one is the printer's *decision machinery*.
