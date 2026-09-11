<!-- capsule-v2 -->
# Markdown policy files — what is the on-disk format and how does the folder stay in sync with storage?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you define policies as markdown-with-frontmatter files and keep bidirectional sync (FS→DB load, DB→FS auto-save, FS-deletion→DB removal) without corrupting guard code that contains `---`?

## Folder loader: frontmatter → typed policies
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/folder_loader.py` (`parse_markdown_with_frontmatter` :28-70, `create_triggers_from_metadata` :73-111, per-type creators :114-328, `POLICY_CREATORS` :331-337, `load_policies_from_folder` :340-424); writer/mirror `src/cuga/backend/cuga_graph/policy/filesystem_sync.py:PolicyFilesystemSync` (`_policy_to_markdown` :81-174, `save_policy_to_file` :176-211, `get_filesystem_policy_ids` :265-302, `sync_removals` :304-337).
**Signature:** `(frontmatter: Dict, content: str) = parse_markdown_with_frontmatter(file_path)`; `await load_policies_from_folder(folder_path, storage, clear_existing=False) -> {"count", "errors", "files"}`; `sync.save_policy_to_file(policy) -> path`; `await sync.sync_removals(storage) -> List[policy_id]`.
**Data Shape:** File = YAML frontmatter between `---` fences + markdown body. Folder layout fixed: `playbooks/ output_formatters/ tool_guides/ intent_guards/ tool_approvals/`. Frontmatter keys: id (default `<type>_<file stem>`), name (REQUIRED), description, triggers `{keywords|natural_language|always, target, case_sensitive, operator, threshold}`, priority 50, enabled true + type-specific (`target_tools`, `tool_guards`, `format_type`, `response_type`, `required_tools`, ...). Body maps to `markdown_content` / `format_config` / `guide_content` / response content.

### Decisive source
```python
# folder_loader.py:45-53 — line-exact fence matching, NOT split('---')
# Check for frontmatter delimiters on their own lines. ToolGuard policy code
# can contain strings/comments with "---", which must not terminate YAML.
lines = content.splitlines(keepends=True)
if not lines or lines[0].rstrip('\r\n') != '---':
    raise ValueError(f"File {file_path} missing frontmatter (should start with ---)")
closing_index = None
for index, line in enumerate(lines[1:], start=1):
    if line.rstrip('\r\n') == '---':
        closing_index = index
        break

# folder_loader.py:398-402 — folder decides default type; frontmatter can override
detected_type = frontmatter.get('type', policy_type)
creator_func = POLICY_CREATORS.get(detected_type)

# filesystem_sync.py:193 — filename IS the id
filename = f"{policy.id}.md"
```

**Flow:** LOAD — walk 5 subfolders → parse each `.md` → creator builds typed policy (missing name ⇒ ValueError; Playbook/IntentGuard require ≥1 trigger; OutputFormatter/ToolGuide fall back to `[AlwaysTrigger()]`; invalid `tool_guards` entries are skipped with a warning, not fatal) → `storage.add_policy` → collect per-file errors, never abort the batch. WRITE (mirror image) — serialize triggers back to flat config, body from the right content field, dump under `<cuga_folder>/<subfolder>/<id>.md`. SYNC — `get_filesystem_policy_ids` re-parses every file to build id set AND refreshes `_policy_files_map`; `sync_removals` deletes storage rows whose ids vanished from disk.
**Invariant:** The closing fence is matched LINE-EXACTLY because embedded `---` inside ToolGuard code blocks would otherwise truncate the YAML (a naive `content.split('---', 2)` breaks exactly the policies carrying guard code). Loaders are per-file fault-isolated; the id↔filename identity is what makes removal sync safe. Trigger defaults are deliberately asymmetric per type: hard requirement for blocking policies (IntentGuard/Playbook), AlwaysTrigger fallback for advisory ones (ToolGuide/OutputFormatter).
**Probe:** `policy/tests/test_filesystem_sync.py` (735 lines): `test_load_from_folder_manual` (:545), `test_load_from_folder_clear_existing` (:578), `test_validation_removes_deleted_fs_policies_from_db` (:498), `test_auto_save_on_add_policy` (:253); round-trip parametrized over all five types (:82-148).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "parse_markdown_with_frontmatter", limit: 3 });
// → folder_loader.py 28-70
```

## Verdict
Adopt the markdown+frontmatter authoring surface, line-exact fence parsing, per-file error isolation, id-named files, and the three-way sync loop (load-on-init / save-on-write / remove-on-delete). Adapt folder names and trigger schema to your host. Omit the SDK/UI wiring that calls it.
