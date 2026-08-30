<!-- capsule-v2 -->
# Config-file safe editing — how do you upsert entries into a user's JSON/TOML/shell config without corrupting or taking ownership of their file?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What preconditions and write protocol preserve comments, BOM, metadata — and refuse unsafe filesystem states?

## Identity/byte CAS + symlink/hardlink fail-closed + managed markers
**Path/Symbol:** `src/cli/config_json_like.h` (contract 7–20) + `src/cli/config_text_edit.h` (managed blocks 9–22); suites tests/test_config_json_like.c, test_config_toml_edit.c, test_config_text_edit.c.
**Signature:** `int cbm_json_like_upsert_entry(const char *file_path, const char *const *object_path, size_t path_len, const char *entry_key, const char *entry_json);` / `int cbm_text_upsert_managed_block(file_path, begin_marker, end_marker, owned_content);`
**Data Shape:** Editors rewrite ONLY missing paths or regular single-link files; POSIX symlinks & Windows reparse points fail closed; owner/group/mode retained across atomic replacement; destination + synced temp revalidated for identity AND bytes immediately before publication.

### Decisive source
```c
/* Editors only rewrite missing paths or regular, single-link config files.
 * POSIX symlinks and Windows reparse points fail closed. Existing POSIX
 * owner/group/mode metadata is retained across the atomic replacement. The
 * destination and synced temporary file are identity/byte revalidated
 * immediately before publication. */
/* [text] Duplicate or unbalanced markers are rejected without changing
   the file. ... preserves user bytes outside the block; idempotent insert. */
```

**Flow:** stat + link-type gate → read snapshot → parse (strict JSON value / JSON5-tolerant with byte-identical decimal rejection / marker-scanned text) → modify in-memory → write temp with fsync → FINAL identity+byte revalidation against the earlier snapshot → rename over, restoring metadata → on any race (target swapped/missing/stale content) refuse without touching the winner.
**Invariant:** The check-then-write window is narrowed to the final revalidation; duplicate/unbalanced markers must leave the file untouched; BOM/comments/CRLF outside managed blocks survive byte-exact.
**Probe:** `tests/test_config_json_like.c:config_json_like_rejects_stale_content_and_cleans_temp`, `config_json_like_preserves_owner_group_and_mode`, `config_json_like_rejects_symlink_without_touching_target`; text twin: `config_text_managed_replace_preserves_crlf_surroundings`, `config_text_managed_malformed_markers_fail_closed`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_json_like_upsert_entry", limit: 5 });
```

## Verdict
Adopt identity-CAS + fail-closed link policy for any tool that edits user config; adapt parsers per format; omit the JSON5 escape quirks if you accept only strict JSON.
