<!-- capsule-v2 -->
# mv cross-filesystem copy + backup resolution — host-env-driven defaults

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** What does moving across filesystems require, and where do backup suffix/method defaults come from in an embedded shell?

## copy plane + backup config
**Path/Symbol:** `crates/pi-builtins/src/mv.rs:` `match_backup_method` (:299), `determine_backup_mode` (:322), `determine_backup_suffix` (:345 — reads HOST env via host.var: VERSION_CONTROL / SIMPLE_BACKUP_SUFFIX), `copy_dir_contents` (:1206), `copy_dir_contents_recursive` (:1242), hardlink-preserving copy (:1346), xattr copy best-effort (:1441).
**Signature:** `fn determine_backup_suffix(matches, host) -> String`; fallback chain CLI flag → env var → `~`.
**Data Shape:** FIFO-aware file type checks (`is_fifo` per platform :999/:1004); recursive dir copy creates destination then walks contents; hardlinked sources re-linked rather than duplicated when possible; xattrs copied only when the filesystem supports them (errors non-fatal).

### Decisive source
```rust
fn determine_backup_suffix(matches: &ArgMatches, host: &Host) -> String {
	// --suffix wins; else exported shell var SIMPLE_BACKUP_SUFFIX via host.var()
	// (the process environment is NOT the shell's); else "~".
}
```
```rust
// test at mv.rs:1953 pins that backup configuration consults the HOST environment.
```

**Flow:** resolve operands against shell cwd → same-directory rename fast path → cross-device: create dest dir tree, copy contents (regular files with hardlink preservation + optional xattrs; fifos by mknod-equivalent; symlinks recreated) then unlink source → backups taken BEFORE overwrite using resolved method/suffix (`numbered`, `existing`, `simple`, `none` via VERSION_CONTROL env or --backup).
**Invariant:** (1) Environment lookups MUST go through Host::var (exported SHELL vars), not std::env — this is the recurring embedded-shell trap and it has a dedicated test. (2) A failed xattr copy must not fail the move. (3) Cross-device moves preserve hardlink RELATIONSHIPS within the moved set, not to unmoved files.
**Probe:** deterministic anchors: `grep -c 'SIMPLE_BACKUP_SUFFIX' crates/pi-builtins/src/mv.rs` ≥ 1; direct test `mv.rs:1953 backup_configuration_uses_host_environment`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "mv backup suffix version control host env", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (mv.rs:345/:1953).

## Verdict
Adopt host-env-first default resolution and the hardlink/xattr-aware cross-device copier for any move/copy tool in an embedded shell. Adapt device-detection to your fs layer; keep backups-before-overwrite ordering.
