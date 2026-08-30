<!-- capsule-v2 -->
# uniq obsolete-flags + jq runtime shim + tee signal policy — three small-faithfulness seams

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** Which small utilities carry non-obvious embedded-shell adaptations a porter would silently drop?

## uniq: obsolete +N/-N merge
**Path/Symbol:** `crates/pi-builtins/src/uniq.rs:` `rewrite_argv` (:760-776), `run_uniq` (:788+).
**Data Shape/Flow:** GNU accepts obsolete `+N` (skip chars) / `-N` (skip fields) POSITIONALLY; the rewriter runs `handle_obsolete`, then appends modern equivalents ONLY IF the corresponding modern flag is absent (`--skip-fields=N` / `--skip-chars=N`) — explicit modern flags win over positional.
**Invariant:** Merge-not-overwrite: `-2 -s1` keeps BOTH skips with modern precedence; validate_special_clap_errors runs before appending so conflicts still fail loudly.
**Probe:** deterministic anchor `grep -c 'fn rewrite_argv' crates/pi-builtins/src/uniq.rs` = 1; test module at uniq.rs tests pins skip arithmetic.

## jq: thread-local RuntimeGuard over jaq
**Path/Symbol:** `crates/pi-builtins/src/jq.rs:` `Runtime { stdout, stderr, env, cancel }` (:968-973), `RUNTIME` thread_local (:973-975), `RuntimeGuard::install/Drop` (:985-999), accessors (:1005-1020), USAGE_ERROR=2 (:921), in-place temp+rename note (:1085+).
**Signature:** `struct RuntimeGuard;` RAII — install clones host stream handles + env vec + cancel Arc into TLS; jaq internals (single-threaded interpreter) call `runtime_env()/runtime_cancelled()` instead of touching process state.
**Invariant:** debug_assert!(slot empty) on install — nested guards are a bug. Color state machine is separate TLS (`color::init` Once wires yansi to it). All operand paths resolved via Host BEFORE interpretation so `$__loc__`-style file errors name shell-relative paths. In-place editing writes sibling temp then renames (sponge pattern).
**Probe:** anchors: `grep -c 'jq runtime is installed' crates/pi-builtins/src/jq.rs` = 3.

## tee: no signal-disposition changes
**Path/Symbol:** `crates/pi-builtins/src/tee.rs:` doc (:1-7), OUTPUT_ERROR modes (:23-26,:40).
**Flow/Invariant:** standalone tee flips SIGINT/SIGPIPE dispositions; an in-process builtin CANNOT — `-i` is accepted and IGNORED (shell policy owns signals), stdout BrokenPipe routes through `--output-error` semantics while remaining outputs still receive their writes. Ports that emulate disposition via libc in-process corrupt the whole shell.
**Probe:** anchor `grep -c 'cannot do that safely' crates/pi-builtins/src/tee.rs` = 1.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "uniq skip fields obsolete jq runtime guard tee output error", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via per-file anchor greps listed above (BM25 ranks these small seams below noise — cite source lines).

## Verdict
Adopt all three micro-contracts: positional-flag merging with modern precedence, TLS runtime shims for single-threaded interpreters inside async shells, and never-touch-signal-disposition in-process. Each is a porting trap with a test or byte-exact diagnostic pinning it.
