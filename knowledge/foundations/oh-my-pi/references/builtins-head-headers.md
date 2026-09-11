<!-- capsule-v2 -->
# head multi-file header discipline — the `first` latch that GNU pins byte-exactly

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** When does `head a b` print the blank separator line, and which failures must NOT flip it?

## print_headers + first latch
**Path/Symbol:** `crates/pi-builtins/src/head.rs:` run (:1374+), `print_header` (:1391-1400), comment :1387-1389; obsolete parser `parse_obsolete` (:131-161) feeding `-N` forms.
**Signature:** `let print_headers = (options.files.len() > 1 && !options.quiet) || options.verbose;`
**Data Shape:** Header = `==> NAME <==\n` preceded by `\n` UNLESS first; NAME is `standard input` for `-`.

### Decisive source
```rust
// GNU head only emits the blank separator line before a header when a
// previous file actually produced output; open failures print nothing
// and must not flip `first`.
let mut first = true;
fn print_header(out: &mut impl Write, name: &[u8], first: &mut bool) {
	if !*first { let _ = writeln!(out); }
	let _ = out.write_all(b"==> ");
	let _ = out.write_all(name);
	let _ = out.write_all(b" <==\n");
	*first = false;
}
```

**Flow:** for each file: open (missing file → stderr diagnostic, continue, exit code 1 at end, `first` untouched) → if headers enabled: print separator+header unless first → copy up to limit bytes → a file that produced ZERO bytes still flips first AFTER its header was printed (header itself counts as output).
**Invariant:** The latch tracks "did we emit anything to stdout yet", not "is this the first file" — that is the entire subtlety; ports keyed on file index emit spurious blank lines after failed operands. Byte-level writes (not writeln! of a formatted string) keep exact GNU bytes.
**Probe:** deterministic anchors: `grep -c 'must not flip' crates/pi-builtins/src/head.rs` = 1; test modules head.rs:254/:677/:1469 pin obsolete parsing and output shapes.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "head print header first blank separator", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (head.rs:1368-1400 block).

## Verdict
Adopt the output-latch header rule for any multi-input printer with separators. Adapt option plumbing; keep byte-exact header framing and the failure-doesn't-flip rule.
