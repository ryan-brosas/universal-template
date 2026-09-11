<!-- capsule-v2 -->
# rm safety rails — empty operand, preserve-root via canonicalize, . / .. refusal

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** Which checks must run BEFORE resolution/metadata so an embedded shell's `rm -rf` cannot destroy the workspace?

## guard ladder in run()
**Path/Symbol:** `crates/pi-builtins/src/rm.rs:` empty-operand guard (:1044-1055), root check (:1057-1068), `is_root_path` (:1256-1268), `show_preserve_root_error` (:1271-1282), `handle_dir` dot-refusal (:1284-1300), interactive wording table (:100-124 doc).
**Signature:** `fn is_root_path(host, path) -> bool`; `fn path_is_current_or_parent_directory(path) -> bool`.
**Data Shape:** Guard ORDER: empty string → trailing-slash+root (BEFORE symlink_metadata so `rootlink/` — a symlink-to-root with slash — is caught by the canonicalizing branch) → per-file metadata dispatch → dir handler re-checks `.`/`..` and root.

### Decisive source
```rust
// An empty operand can never name a real file. Guard it BEFORE `Host::resolve`,
// which joins "" onto the shell's working directory — without this, `rm -rf ""`
// RESOLVES TO THE CWD and recursively deletes it. GNU rm reports ENOENT for an
// empty operand (and `rm -f` stays silent), so mirror that here.
if filename.is_empty() { if !options.force { show_error!(...NoSuchFile...) } continue; }
```
```rust
fn is_root_path(host: &mut Host, path: &Path) -> bool {
	if path.has_root() && path.parent().is_none() { return true; }        // literal "/"
	if let Ok(canonical) = host.resolve(path).canonicalize() {
		canonical.has_root() && canonical.parent().is_none()              // symlink to /
	} else { false }
}
```

**Flow:** operand loop accumulates had_err without aborting (`bitor`) → dirs: clean trailing slashes FIRST (else `dir///` misclassifies), refuse current/parent dir outright, then recursive vs plain-dir path with preserve-root veto producing the two-line GNU diagnostic ("it is dangerous to operate recursively on X (same as '/')" + "use --no-preserve-root").
**Invariant:** (1) The Host::resolve("") join hazard is embedded-shell-specific — process-cwd CLIs never see it; any resolve-based port needs the same pre-guard. (2) Root detection is canonicalize-based, not string-based. (3) `-f` suppresses the ENOENT diagnostic but NOT the structural refusals. (4) Interactive prompt picks wording by writability (protected vs normal), with PromptProtected as default mode.
**Probe:** deterministic anchors: `grep -c 'resolves to the cwd' crates/pi-builtins/src/rm.rs` = 1; `grep -c 'same as' crates/pi-builtins/src/rm.rs` ≥ 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "rm preserve root canonicalize empty operand", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (rm.rs:1049/:1256).

## Verdict
Adopt the guard order verbatim for any destructive tool inside a shell whose resolve() joins to workspace cwd. Adapt diagnostics; keep canonicalize-based root identity and the silent-force ENOENT behavior.
