<!-- capsule-v2 -->
# format_args!/write!/format! macro stack — how does rule code emit IR without allocating or naming FormatElement?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter adding a language formatter must reproduce the macro stack that turns `[token("a"), space()]` bracket lists into `Arguments` — what exactly does each layer do, and why does the whole path stay heap-free?

## Macro cascade (macros.rs, all five `macro_rules!`)
**Path/Symbol:** `crates/biome_formatter/src/macros.rs:30-38` (`format_args!`), `:70-75` (`write!`), `:101-115` (`dbg_write!`), `:141-145` (`format!`), `:330-334` (`best_fitting!`).
**Signature:** `format_args!($($value:expr),+) => Arguments::new(&[Argument::new(&$value)])`; `write!($dst:expr, [$($arg:expr),+]) => $dst.write_fmt(format_args!(...))`.
**Data Shape:** `Arguments<'a, Context>` wraps a fixed-size slice of `Argument` newtypes holding `&dyn Format` refs — zero allocation; the bracket list syntax `[a, b]` is just an array literal, not a macro-special syntax.

### Decisive source
```rust
// macros.rs:30-38
macro_rules! format_args {
    ($($value:expr),+ $(,)?) => {
        $crate::Arguments::new(&[
            $(
                $crate::Argument::new(&$value)
            ),+
        ])
    }
}
// macros.rs:70-75
macro_rules! write {
    ($dst:expr, [$($arg:expr),+ $(,)?]) => {{
        let result = $dst.write_fmt($crate::format_args!($($arg),+));
        result
    }}
}
```

**Flow:** rule code calls `write!(f, [elements])` → expands to `f.write_fmt(Arguments::new(&[Argument::new(&el)...]))` → `Formatter::write_fmt` iterates arguments, calling each element's `Format::fmt(f)` → those fmt bodies call `f.write_element(...)` into the Vec-backed buffer. `format!(context, [args])` composes `crate::format(context, format_args!(...))` to produce a `Formatted` document in one shot.
**Invariant:** The macro takes arguments **by reference** (`&$value`) and never clones or boxes; temporaries inside the bracket list must outlive the `write!` statement. A porter replacing macros with a varargs function loses temporary lifetime extension and will hit borrow errors — keep the macro shape.
**Probe:** `grep -n 'least_expanded:expr' crates/biome_formatter/src/macros.rs` → `331:` (best_fitting's head pattern); `grep -c 'macro_rules!' crates/biome_formatter/src/macros.rs` → `5`; `grep -n '\$dst.write_fmt' crates/biome_formatter/src/macros.rs` → `72:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"format_args write macro Arguments","limit":6,"detail":"ids"}'
```
Resolves `biome.crates.biome_formatter.src.arguments.*` (Arguments/Argument structs); note `macro_rules!` definitions themselves are NOT indexed symbols — anchor on the structs they construct.

## Verdict
Adopt the three-layer cascade (bracket array → format_args! by-ref Arguments → write_fmt loop) verbatim; adopt `dbg_write!` only as a dev tool (`inspect()` + `eprintln!` per element, file!()/line!() tagged — macros.rs:101-115). Omit Rust-specific token-pasting details; any host language needs an equivalent by-reference argument pack plus a writer entry point. Direct tests: `test_single_element`/`test_multiple_elements` (macros.rs:350-383) pin exact `FormatElement` vec output through `write![&mut buffer, [...]]`.
