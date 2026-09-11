<!-- capsule-v2 -->
# cut matcher abstraction — memchr field splitting for exact and whitespace delimiters

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** How does `-f` with a multi-byte delimiter or `-d ' '` (any-run-of-whitespace) split without regex?

## Matcher trait + implementations
**Path/Symbol:** `crates/pi-builtins/src/cut.rs:` `trait Matcher` (:52-54), `ExactMatcher` (:57-82), `WhitespaceMatcher` (:85-101), tests (:109-134+), rewrite_argv `-d=` note (:28-35).
**Signature:** `fn next_match(&self, haystack: &[u8]) -> Option<(usize, usize)>` — returns [first,last) span of the next DELIMITER occurrence.
**Data Shape:** ExactMatcher asserts non-empty needle; scans with `memchr(needle[0])` then prefix-checks the tail — first-byte prefilter avoids per-position compare. WhitespaceMatcher: `memchr2(b' ', b'\t')` then consumes the whole run, so consecutive separators are ONE delimiter (GNU behavior for the non-standard whitespace mode).

### Decisive source
```rust
impl Matcher for ExactMatcher<'_> {
	fn next_match(&self, haystack: &[u8]) -> Option<(usize, usize)> {
		let mut pos = 0usize;
		loop {
			let match_idx = memchr(self.needle[0], &haystack[pos..])?;
			let match_idx = match_idx + pos; // account for starting from pos
			if self.needle.len() == 1 || haystack[match_idx + 1..].starts_with(&self.needle[1..]) {
				return Some((match_idx, match_idx + self.needle.len()));
			}
			pos = match_idx + 1;
		}
	}
}
```

**Flow:** select matcher by delimiter spec → per line: walk matches; fields = spans between; `-f` ranges (incl. open-ended `3-`, complement via `--complement`) resolved against field indices → output joined by OUTPUT delimiter (`--output-delimiter` may differ).
**Invariant:** (1) Empty needle is a panic-by-contract (assert) — callers guarantee `-d` non-empty after rewrite. (2) Byte-span semantics mean multi-byte UTF-8 delimiters work but fields are byte-indexed — character semantics only when delimiter is single-byte ASCII. (3) The whitespace mode collapses runs; exact mode does not (`a,,b` has an empty field).
**Probe:** direct tests pin spans byte-exactly: `cut.rs:109 test_exact_matcher_single_byte`, :120 `test_exact_matcher_multi_bytes`, :131 `test_whitespace_matcher_single_space`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "cut matcher next_match whitespace exact", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (cut.rs:57/:85).

## Verdict
Adopt the two-implementation Matcher split for column tools — it is the fast, allocation-free core that regex-based splitters lose to. Adapt to your SIMD search crates; keep run-collapsing ONLY in the whitespace mode.
