<!-- capsule-v2 -->
# sponge atomic soak — delayed open + sibling-temp rename

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (moreutils port); Codebase Memory `oh-my-pi`. **Question:** Why is `command < file | sponge file` safe here, and what does the replace path guarantee readers never see?

## soak_stdin → replace_atomically
**Path/Symbol:** `crates/pi-builtins/src/sponge.rs:` `run` (:36-69), `soak_stdin` (:106-121), `replace_atomically` (:132-139), `write_and_swap` (:141-153), `create_sibling_temp` (:157-186).
**Signature:** `fn soak_stdin(host) -> Result<Vec<u8>, SoakError>` (Cancelled | Io); `fn create_sibling_temp(target) -> io::Result<(PathBuf, File)>`.
**Data Shape:** 64 KiB read chunks; temp name `.<base>.sponge.<tag:016x>` where tag = nanos·0x9e3779b97f4a7c15 (golden-ratio hash) + AtomicU64 counter + pid; ≤32 create_new retries on collision.

### Decisive source
```rust
// Soak before resolving or opening the destination. In particular, do not move
// this below the output-operand branch: stdin may be that same file.
let buffer = match soak_stdin(host) { ... };
...
// Writes `buffer` to a fresh temporary file beside `target`, copies the existing
// target's permissions onto it, then renames it over the target so readers
// NEVER OBSERVE A TRUNCATED FILE.
temp.write_all(buffer)?; temp.flush()?;
if let Ok(metadata) = fs::metadata(target) { fs::set_permissions(temp_path, metadata.permissions())?; }
fs::rename(temp_path, target)
```

**Flow:** read stdin to EOF polling cancellation BETWEEN chunks (aborted pipeline never touches the destination — cancelled ⇒ exit 130, file untouched) → no operand ⇒ stdout passthrough → append mode opens in-place append → replace mode writes sibling temp, flush, copy permissions (best-effort metadata read BEFORE rename), rename over target; on any failure the temp is removed.
**Invariant:** (1) The delayed open IS the correctness property: opening/truncating the destination before EOF would destroy the data still flowing through the pipe. (2) Temp lives in the target's DIRECTORY (same filesystem — rename must be atomic). (3) Permissions are preserved on replace (0o600 test pins it); append path needs none. (4) Cancellation checked both before each read and after an Ok(0).
**Probe:** direct tests pin all legs from repo root paths: `sponge.rs:201 stdin_written_to_file_exactly`, :225 `replaces_existing_target_and_leaves_no_temp_files` (asserts zero leftover files), :241 `permissions_preserved_on_replace`, :268 `soaks_existing_target_before_replacing_it` (stdin redirected FROM the target itself).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "soak_stdin sponge atomic replace", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `soak_stdin sponge.rs:106-121`, rank-2 `replace_atomically :132-139`.

## Verdict
Adopt soak-before-open + same-directory temp + permission-preserving rename for any read-modify-write-file filter. Adapt the name generator; keep the golden-ratio+pid collision mix and the remove-temp-on-failure cleanup.
