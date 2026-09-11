<!-- capsule-v2 -->
# Bounded streaming think-tag filter — how do you strip inline <think>/<thinking> tags from token streams without corruption or unbounded buffering?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how do you extract reasoning wrapped in <think>/<thinking> tags from a CHUNKED token stream, handling tags split across chunk boundaries, quoted '>' in attributes, self-closing tags, nesting, and adversarially large tag-like prefixes?

## ThinkFilter push/finish state machine
**Path/Symbol:** `crates/goose-provider-types/src/thinking.rs:ThinkFilter` (24-156), `next_buffer_event` (164-186), `parse_think_tag` (188-268), `is_possible_partial_think_tag` (270-286), `MAX_BUFFERED_THINK_TAG_BYTES = 8 * 1024` (7).
**Signature:** `fn push(&mut self, chunk: &str) -> FilterOut`; `fn finish(mut self) -> FilterOut`; `struct FilterOut { content: String, thinking: String }`; free helper `pub fn split_think_blocks(text: &str) -> (String, String)`.
**Data Shape:** incremental in/out buffers; state = `inside_think` + `think_depth` (nesting); unmatched '<'-prefixes stay buffered until resolvable or oversized.

### Decisive source
```rust
// thinking.rs — partial-tag handling and hard buffer bounds
Some(BufferEvent::Partial(pos)) => {
    emit_prefix_if_any();                       // bytes before the candidate flush normally
    if self.buffer.len() > MAX_BUFFERED_THINK_TAG_BYTES {
        let oversized = std::mem::take(&mut self.buffer);   // release: emit verbatim
        if self.inside_think { out.thinking.push_str(&oversized); }
        else                 { out.content.push_str(&oversized); }
    }
    break;
}
...
// parse_think_tag requires a REAL boundary after the name (>, /, whitespace):
// "<thinking-mode>" and "<thinking123>" are NOT think tags and must survive in content.
let valid_open_boundary = match bytes.get(idx) {
    Some(&b) => b == b'>' || b == b'/' || b.is_ascii_whitespace(),
    None => false,
};
// Self-closing <think/> is a NO-OP: never flips inside_think, never leaks into content,
// and does NOT close an enclosing open block (depth stays until real </think>).
```

**Flow:** push(chunk) appends to buffer → loop: find next decisive event = complete Open/Close/SelfClosing tag (quote-aware attribute scan), oversized tag (>8KiB ⇒ emitted verbatim, buffer released), partial candidate ('<' + prefix matching bounded open/close regexes with no unquoted '>') ⇒ hold, or plain text ⇒ route by `inside_think`. finish(): remaining buffer routes to thinking if inside an unterminated block, else content; capacity is re-bounded after processing.
**Invariant:** routing is decided ONLY by tag events — quoted `>` inside attributes never terminates a scan; a chunk boundary anywhere inside `<think`, `</think`, or a self-closing form is held, never leaked; self-closing tags neither open nor close; depth>1 nesting collapses correctly on the outer close; memory is capped at 8KiB buffered even under pathological input.
**Probe:** `cargo test -p goose-provider-types --lib thinking` — included in the observed GREEN run (551 passed / 0 failed): `test_split_think_blocks_*` (inline/case/multiple/attributes/quoted-gt/thinking-variant), `test_think_filter_streaming_across_partial_tags`, `test_think_filter_treats_self_closing_as_noop`, `test_think_filter_self_closing_does_not_swallow_following_content` + `..._across_self_closing_boundary` + `..._inside_open_block_closes_nothing` (regressions), `test_think_filter_bounds_unterminated_quoted_tag_candidates`, `test_think_filter_releases_single_oversized_candidate_allocation`, `test_think_filter_accepts_bounded_streamed_attributes`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "ThinkFilter split_think_blocks next_buffer_event", limit: 8 });
// located: next_buffer_event 164-186, split_think_blocks 9-16, plus the split/filter regression tests
```

## Verdict
Adopt the push/finish two-method API, the 8KiB partial-tag bound with verbatim-emit release, the exact-name-with-boundary tag match, and the self-closing/noop + quoted-gt rules verbatim — they encode five separate regression fixes. Adapt the accepted tag names to your models' dialect (goose accepts think/thinking case-insensitively). Omit the Gemini `thoughtSignature` key constant unless replaying Gemini reasoning. Coverage: thinking.rs `no_recorded_issue` + `metadata_match`; direct tests GREEN.
