<!-- capsule-v2 -->
# align vs indent dual indent semantics — when does an aligned region change indention LEVEL versus literal spaces?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter implementing Prettier's `align` must know how `align("  ", content)` interacts with nested `indent()` under tab vs space styles — the two produce DIFFERENT output.

## Align placeholder + AlignedStr refcounted variant
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:1243-1412` (docs, `align()`, `Align`, `AlignedStr`, `Format::fmt`), contrast `indent` :1003-1023 (`StartIndent`/`EndIndent` tags), `dedent` :1160+, `dedent_to_root` :1233+.
**Signature:** `pub fn align<'a>(placeholder: impl Into<AlignedStr>, content: &'a Content) -> Align<'a, Context>`; `enum AlignedStr { Borrowed(&'static str), Owned(std::rc::Rc<str>) }`.
**Data Shape:** Align carries a literal placeholder string (printed per continuation line) plus content; Indent/Dedent carry no parameters — they shift LEVEL by ±1 against the configured indent character.

### Decisive source
```rust
// builders.rs:1363-1372 — the Rc variant exists because the PRINTER clones per line break
/// Placeholder text printed as alignment on continuation lines.
///
/// The printer clones this value on every line break inside an aligned
/// region (see `pending_indent`), so the owned variant is reference-counted
/// to keep those clones allocation-free.
pub enum AlignedStr {
    Borrowed(&'static str),
    Owned(std::rc::Rc<str>),
}
```

**Flow:** `align("  ", c)` prints `c`'s continuation lines prefixed by the two-space placeholder → if `c` contains `indent(...)`: under Tab style the inner indent raises the level by one (output shows one MORE tab than the align alone would suggest); under Space style the inner indent contributes its full width AND the align keeps adding its literal spaces — the two stack visibly differently (doc examples :1259-1296 vs :1300-1343 show both outputs verbatim).
**Invariants:** (1) `align` NEVER changes the indention level — it splices literal spaces; `indent` changes ONLY the level. Mixing them is not associative across styles: `align > indent ≠ indent > align` under spaces. (2) Use `align` only when a specific space count is required; otherwise prefer `indent` to respect user's indent-style option (:1245-1249). (3) Placeholder must be owned-or-static because continuation-line cloning happens per soft/hard line inside the region — hence `Rc<str>`; porting with plain `String` clones per line allocates per break.
**Probe:** `grep -c 'Owned(std::rc::Rc<str>)' crates/biome_formatter/src/builders.rs` → `1`; `grep -c 'pending_indent' crates/biome_formatter/src/builders.rs` → `1`; `grep -n 'Tag(StartIndent)?' crates/biome_formatter/src/builders.rs` → `1019:` (indent's tag pair, contrast align's element form).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"AlignedStr align placeholder","limit":6,"detail":"ids"}'
```
Resolves `AlignedStr.len/is_empty/as_str/from` Methods line-exact (1375-1407).

## Verdict
Adopt the level-vs-literal-spaces split and the Rc'd placeholder rationale; adapt AlignedStr to your host's cheap-clone type (Rc/Arc/interned string). Omit nothing from the doc examples — they ARE the spec for cross-style behavior. Direct tests: both doc examples assert exact multi-line output including `? function () {` alignment under tabs and the 12-space case under spaces.
