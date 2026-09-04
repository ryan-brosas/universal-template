<!-- capsule-v2 -->
# Diagnostic advice pipeline — how does a structured diagnostic become terminal output without losing structure?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you render diagnostics through a visitor pipeline that supports four output modes while keeping markup intact end-to-end?

## PrintDiagnostic mode matrix + print_advices
**Path/Symbol:** `crates/biome_diagnostics/src/display.rs:PrintDiagnostic` (:40-109), `print_advices` (:334-373), `PrintAdvices: Visit` impl (:472-565), `PrintHeader` (:182-255), `print_concise` (:261-293).
**Signature:** `PrintDiagnostic::{simple, verbose, search, concise}(diag) -> Self`; `fn fmt(&self, fmt: &mut fmt::Formatter<'_>) -> io::Result<()>` over `biome_console::fmt`; `fn print_advices<V: Visit, D: Diagnostic + ?Sized>(visitor: &mut V, diagnostic: &D, verbose: bool) -> io::Result<()>`.
**Data Shape:** Diagnostic trait surface consumed here: `message/advices/verbose_advices/location/tags/severity/category/source`; advice vocabulary = log/list/frame/diff/backtrace/command/group/table.

### Decisive source
```rust
// display.rs:334-357 — the whole render is TWO advices walks plus tag
// synthesis; the pre-pass decides frame suppression, then message +
// user advices + synthesized tag warnings are recorded in order
let mut frame_visitor = FrameVisitor { location: diagnostic.location(), skip_frame: false };
diagnostic.advices(&mut frame_visitor)?;          // pass 1: detect frames
let skip_frame = frame_visitor.skip_frame;
print_message_advice(visitor, diagnostic, skip_frame)?;  // message (+code frame)
diagnostic.advices(visitor)?;                     // pass 2: real rendering
print_tags_advices(visitor, diagnostic)?;         // fatal/internal → warn lines
```

**Flow:** concise mode = one line (`{icon} {path}:{line}:{col}: {category}: {message}`, :261-293) → otherwise header (`path:1:1 category [FIXABLE] ━━━…`) then IndentWriter-wrapped advices → verbose adds a "Verbose advice" record_group only if CountAdvices found ≥1 (:360-370) → search mode renders ONLY highlighted frames (PrintSearch visitor, :463-469) for grep integration.
**Invariant:** Markup flows as data (`MarkupBuf`) from diagnostic to terminal — never stringified mid-pipeline; `markup_to_string` exists only at final sink boundaries. Message severity maps to LogCategory icons (✖/⚠/ℹ). Empty message renders a dim "no diagnostic message provided" fallback instead of blank output.
**Probe:** In-file snapshot tests pin exact rendered markup per advice type: `display.rs:973-1234` — `test_header`, `test_log_advices`, `test_list_advice`, `test_frame_advice`, `test_diff_advice`, `test_backtrace_advice`, `test_command_advice`, `test_group_advice`, `test_concise_with_location`, `test_concise_without_location` (13 `#[test]`s total incl. location.rs).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "PrintDiagnostic", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the two-pass advice walk + mode matrix verbatim. Adapt the markup/console layer to your host's styling system. Omit the table renderer's debug_assert contract if you lack an equivalent.
