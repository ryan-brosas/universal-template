<!-- capsule-v2 -->
# tail follow machinery — notify backend ladder, orphan/parent-dir watch strategy

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** How does `tail -f` survive inotify exhaustion and missing/replaced files?

## Watcher start + init_files
**Path/Symbol:** `crates/pi-builtins/src/tail.rs:` `start` (:1747-1811), watcher-config note :1770-1779, ENFILE fallback (:1786-1802), `init_files` (:1829-1860), follow-mode derivation :192-217.
**Signature:** `-F` ⇒ `--follow=name --retry`; plain `-f`/`--follow=descriptor` follows the fd; order-sensitive: `-F` AFTER `--follow=name` wins (index comparison).
**Data Shape:** `notify::Config::with_poll_interval(sleep_sec).with_compare_contents(true)` — compare_contents is REQUIRED to pass GNU `F-vs-rename.sh` despite the hashing cost.

### Decisive source
```rust
match RecommendedWatcher::new(tx, Config::default()) {
	Ok(w) => watcher = Box::new(w),
	Err(e) if e.to_string().starts_with("Too many open files") => {
		// Could be tested with decreasing max_user_instances, e.g.:
		//   sudo sysctl fs.inotify.max_user_instances=64
		writeln!(self.stderr, "tail: {} cannot be used, reverting to polling: Too many open files", text::BACKEND)?;
		host.fail(1);
		self.use_polling = true;
		watcher = Box::new(notify::PollWatcher::new(tx_clone, watcher_config).unwrap());
	},
	Err(e) => return Err(TailError::message(e.to_string())),
}
```
```rust
if path.is_tailable() {        // existing regular file -> watch it directly
	watcher_rx.watch_with_parent(&path)?;
} else if !path.is_orphan() {  // watch PARENT dir non-recursively; retry may find it later
	watcher_rx.watch(path.parent().unwrap(), RecursiveMode::NonRecursive)?;
	if path.is_symlink() { self.orphans.push(path); }  // symlink targets may appear
} else {
	self.orphans.push(path);       // no parent at all -> pure orphan polling
}
```

**Flow:** derive mode from -f/-F/--follow/--retry with argument-order tie rules → choose backend: explicit --use-polling, else RecommendedWatcher (inotify on linux; kqueue FORCED on macOS because FSEvents delays modify events until close — upstream notify#240), ENFILE-class failure degrades to PollWatcher with warning + host.fail(1) → register tailables / parent dirs / orphans → event loop appends growth.
**Invariant:** (1) Backend degradation is a WARNING + exit-1-note, never a hard failure. (2) Relative watch paths are absolutized against cwd BEFORE watching (watchers outlive cwd changes conceptually). (3) Non-linux unix skips non-file paths at init. (4) Hidden triple-hyphen options (`---disable-inotify`, `---presume-input-pipe`) are deliberate GNU-compat spellings.
**Probe:** deterministic anchors: `grep -c 'with_compare_contents' crates/pi-builtins/src/tail.rs` = 1; `grep -c 'reverting to polling' crates/pi-builtins/src/tail.rs` = 1; test modules at tail.rs:516/:1243/:2370 pin filter/signum parsing (runner blocked this environment).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "tail follow watcher poller rename", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps at pin (BM25 for this seam is dominated by sed/mktemp noise — cite source lines).

## Verdict
Adopt the backend-degradation ladder + tailable/orphan/parent watch trichotomy for any file-follow feature. Adapt notify to your watcher crate but keep compare_contents-for-renames rationale and the -F ordering rules. Omit FSEvents notes outside macOS.
