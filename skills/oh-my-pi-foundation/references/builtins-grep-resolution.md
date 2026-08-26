<!-- capsule-v2 -->
# grep on ripgrep libraries — context normalization, literal escaping, PCRE2 JIT probe

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How does GNU-grep compatibility sit on top of grep-searcher, and which argv quirks are normalized pre-clap?

## GrepArgs resolution + normalize_context_args
**Path/Symbol:** `crates/pi-builtins/src/grep.rs:` module doc (:1-3), `pcre2_jit_enabled` (:28), resolver fns (:420-560: match mode / ignore case / filename prefix / file-list modes / context / group separator / directory action / follow links / binary files / max count), `normalize_context_args` (:567+), `escape_literal` (:593+).
**Signature:** `fn resolve_context(cli, matches) -> (usize, usize)` (before/after); `fn escape_literal(pat: &str) -> String` over META char set.
**Data Shape:** Matching = `grep-regex`/`grep-searcher`; recursive walks = pi_walker; `-P` switches to a PCRE2 matcher whose JIT availability is PROBED per host and reported (`--debug`) rather than assumed.

### Decisive source
```rust
// normalize_context_args: GNU accepts `-C 2 -C3 -C=3`-style spellings and
// -A/-B values glued to the flag; clap models only some of them, so argv is
// rewritten into long forms before parsing.
```
```rust
// last_index + choose_latest: repeated exclusive flags resolve to the LAST
// occurrence (GNU semantics), tracked by argv index not insertion order.
```

**Flow:** rewrite argv (context spellings) → resolve ladder of small pure functions each owning one option family (latest-wins by index) → build matcher (default regex set; -F uses escaped-literal matcher; -P PCRE2 with jit_enabled probe) → searcher with binary-mode + max-count plumbing → walker applies include/exclude rules (`allows_file`/`allows_dir` over ordered PathRule list, suffix-glob matching).
**Invariant:** (1) Directory action default (read/skip/recurse) must mirror grep's "recurse only with -r/-R" split. (2) Binary handling maps to BinaryFiles settings consumed by the searcher — never custom heuristics in the sink. (3) Exit status is grep's: 0 match, 1 no match, 2 error — errors during walk keep counting.
**Probe:** deterministic anchors: `grep -c 'fn normalize_context_args' crates/pi-builtins/src/grep.rs` = 1; `grep -c 'fn pcre2_jit_enabled' crates/pi-builtins/src/grep.rs` = 1; tests at grep.rs:1554.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "grep pcre2 jit enabled context args normalize", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (`pcre2_jit_enabled` grep.rs:28).

## Verdict
Adopt the resolver-function decomposition + latest-wins index tracking + JIT probe pattern for any grep port over library searchers. Adapt to your regex crates; keep the exit-status contract and directory-action defaults.
