<!-- capsule-v2 -->
# Terminal-emulator header workarounds — how do you emit clickable diagnostics that survive VS Code and JetBrains terminals?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How should `path:line:col` headers adapt per hosting terminal so links actually open?

## print_file_location + is_terminal_program
**Path/Symbol:** `crates/biome_diagnostics/src/display.rs:print_file_location` (:114-159), `is_terminal_program` (:763-773); width policy in `PrintHeader::fmt` (:242-253).
**Signature:** `fn print_file_location<D: Diagnostic + ?Sized>(fmt, diagnostic) -> io::Result<()>`; `fn is_terminal_program(name: &str) -> bool { env::var("TERM_PROGRAM").is_ok_and(|p| p == name) || env::var("TERMINAL_EMULATOR").is_ok_and(|p| p == name) }`.
**Data Shape:** three-way branch keyed on `TERM_PROGRAM`/`TERMINAL_EMULATOR`: "vscode" | "JetBrains-JediTerm" | other; absolute paths get `file://` Hyperlink markup.

### Decisive source
```rust
// display.rs:124-143 — per-host location rendering; JetBrains wants a bare
// " at <path>" suffix (its console parses that), VS Code wants the raw
// path with NO hyperlink markup (it linkifies plain text itself)
let is_vscode = is_terminal_program("vscode");
let is_jetbrains = is_terminal_program("JetBrains-JediTerm");
…
if is_vscode {
    fmt.write_str(name)?;
} else if is_jetbrains {
    fmt.write_str(&format!(" at {name}"))?;
} else if path_name.is_absolute() {
    let link = format!("file://{name}");
    fmt.write_markup(markup! { <Hyperlink href={link}>{name}</Hyperlink> })?;
}
```

**Flow:** header/concise both call print_file_location → line:col appended ONLY when BOTH span and source_code exist (offset→line conversion needs the text, :148-155) → category rendered via `print_category` with doc-link hyperlink when the category has one (:164-179) → rule line padded to `min(terminal_width, debug=100)` with `━`, floor 10 chars (`MIN_WIDTH`), measured through a CountWidth writer (:297-331).
**Invariant:** Debug builds hardcode 100 columns and force `is_terminal_program → false` (cfg!(debug_assertions)) so snapshot tests are host-independent — a porter running link logic under test frameworks will flake without this. The JetBrains branch exists for jediterm's parser (issue-linked comments :767-769).
**Probe:** In-file `test_header` (display.rs:973-995) pins exact `path:1:1 internalError/io <FIXABLE> ━━…` output including padding width.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "print_file_location", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the three-host ladder + test-stability gates verbatim. Adapt host names as your ecosystem evolves. Omit nothing — this encodes real terminal-compat bug history.
