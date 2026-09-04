<!-- capsule-v2 -->
# Printer call/indent stack split — how do fits-checking and printing share state without corrupting it?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** the printer must speculatively run `fits` over future elements using the CURRENT indent/tag stacks — what architecture keeps that measurement from mutating print state?

## The dual-stack seam
**Path/Symbol:** `crates/biome_formatter/src/printer/call_stack.rs` — `CallStack::pop(kind)` with Root-frame resurrection (:70-105), `FitsCallStack` as a VIEW over `PrintCallStack` (:181-207), `SuffixStack` (:212-218), `IndentStack` dedent/history algebra (:225-261), `PrintIndentStack` + `flush_suffixes` (:264-304), `FitsIndentStack` two-view construction (:308-344).
**Signature:** `PrintCallStack(Vec<StackFrame>)` owned; `FitsCallStack { stack: StackedStack<'print, StackFrame> }` borrowed (`StackedStack::with_vec(&print.0, saved)`); frames carry only `{ kind: Root|Tag(TagKind), args: PrintElementArgs { mode: PrintMode } }` — "passed by value … isn't storing any heavy data structures" (:21-27 doc).
**Data Shape:** three parallel Indention stacks on the print side: current `indentions`, `history_indentions` (dedent save), `suffix_indentions` (line-suffix context); fits side mirrors each as a `StackedStack` view = borrowed base slice + saved overflow Vec.

### Decisive source
```rust
// call_stack.rs:86-98 — popping the sentinel is an ERROR but must not
// underflow: the Root frame is pushed back so "the stack is never empty":
Some(frame @ StackFrame { kind: StackFrameKind::Root, .. }) => {
    // Put it back in to guarantee that the stack is never empty
    self.stack_mut().push(frame);
    Err(PrintError::InvalidDocument(Self::invalid_document_error(kind, None)))
}
// IndentStack dedent round-trip (:234-243): Dedent pops current→history;
// EndDedent pops history→current. Fits runs the SAME trait methods against
// views, so a speculative Dedent/EndDedent pair leaves print state untouched.
```
**Flow:** print loop pushes a frame per Start-tag and pops via `pop(end_kind)`, which validates start/end pairing into `InvalidDocumentError::{StartTagMissing, StartEndTagMismatch}`; `top()` clones args for element printing; Indent/Align push incremented/set-align Indention, Dedent rotates through history, LineSuffix contexts park their indention on the suffix stack until `flush_suffixes` replays them in reverse. `fits_element` constructs `FitsCallStack::new(&print_stack, saved_frames)` + `FitsIndentStack` (both views), measures, then `finish()/into_vec()` discards or restores the saved tails.
**Invariant:** tag start/end pairing errors are DATA (InvalidDocument) not panics — malformed IR fails formatting with a diagnosable error; the Root sentinel makes every pop total. Porters who let fits mutate the real indent stack produce correct-looking single-line output but corrupt indentation of everything printed AFTER a fits probe that crossed a Dedent; porters who drop flush_suffixes' reverse replay misindent deferred line comments under nested indents.
**Probe:** `crates/biome_formatter/src/printer/mod.rs` test mod :1623+ (fits-on-elements cases at :1664/:1678/:1707 pin fit/fail polarity through the public printer API); `crates/biome_formatter/src/printer/queue.rs` companion capsule `printer-fits-queue.md` covers the queue half.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FitsCallStack StackedStack PrintIndentStack", limit: 10, fields: ["signature", "name", "file"] });
// FitsCallStack::new call_stack.rs 186-195 (line-exact)
```

## Verdict
Adopt the view-over-owned-state pattern for any speculative measurement pass over shared printer state; adapt `Indention` to your indent representation; omit the suffix stack if your IR lacks line-suffix elements. Coverage caveat: stack internals are exercised through printer-level tests rather than direct unit tests here.
