<!-- capsule-v2 -->
# fd fast-path gate — when does the walker skip ignore machinery entirely?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** Under which exact conditions may fd use the collect-free walker fast path, and what walk decisions drive pruning?

## can_use_fast_search + WalkDecision ladder
**Path/Symbol:** `crates/pi-builtins/src/fd.rs:` `const fn can_use_fast_search` (:808-813), `fast_type_filter_supported` (:815-817), `process_walker_entry` (:819-860), `fd_walk_request` (:717-739), slow path with `collect_with_heartbeat` (:683-714).
**Signature:** `fn process_walker_entry(...) -> io::Result<pi_walker::WalkDecision>` — Skip | SkipDescend | Stop | Include.
**Data Shape:** Fast path buffers ALL output in memory and flushes once at end (`BufWriter<Vec<u8>>` → stdout); heartbeat closure polled by the walker so cancellation is observed inside native traversal.

### Decisive source
```rust
const fn can_use_fast_search(cli: &FdCli, config: &SearchConfig) -> bool {
	no_ignore(cli)                 // no --no-ignore-vcs / --no-ignore requests
		&& cli.ignore_files.is_empty()   // no .fdignore files in play
		&& !cli.one_file_system          // not constrained to one mount
		&& fast_type_filter_supported(&config.types)  // no socket/pipe/block/char filters
}
```
```rust
if depth == 0 && is_directory { return Ok(WalkDecision::Skip); }   // never emit the root dir itself
if config.excludes.matches(path, &config.base_dir) { return Skip / SkipDescend }
if ignore_contains.iter().any(|name| path.join(name).exists()) { return SkipDescend; }
```

**Flow:** eligibility const-check → per entry: root-dir suppression → exclude matcher (dir ⇒ prune subtree) → ignore-contains marker dirs (`.git` etc.) prune descent → optional prune-pattern match on directories only → symlink_metadata + type/depth filters → pattern match on display target → emit; cancel or max_results reached ⇒ WalkDecision::Stop at BOTH the walker callback level and between search paths.
**Invariant:** (1) The gate is conservative: ANY gitignore/ignore-file/mount/type-filter requirement silently falls back to the full collector that consults pi-walker's gitignore machinery. (2) `emit_root(true)` + depth-0-dir Skip = "walk from root but don't list it" — deleting this pair changes output for the default invocation. (3) WalkError::Interrupted during a requested cancel is a clean break, not an error.
**Probe:** deterministic anchors: `grep -c 'fn can_use_fast_search' crates/pi-builtins/src/fd.rs` = 1; `grep -c 'WalkDecision::SkipDescend' crates/pi-builtins/src/fd.rs` ≥ 2. Direct-test coverage: fd suite lives under crate tests (runner blocked this environment — stable toolchain vs workspace portable_simd dep).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "fd walk request heartbeat collect", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (`can_use_fast_search` fd.rs:808).

## Verdict
Adopt the two-tier walk design (heartbeat-driven streaming collector + buffered fast path behind a conservative const gate) for any find-like tool. Adapt WalkDecision to your walker; keep root-emission suppression and marker-dir pruning semantics.
