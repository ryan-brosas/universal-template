<!-- capsule-v2 -->
# Secrets-dir scanning — how are secret directories scanned, ordered, and decoded?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** Docker/K8s secret dirs contain one file per field — what are the exact lookup, precedence, error, and decoding rules a porter must reproduce?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/secrets.py:SecretsSettingsSource` (27-147) — `__call__` (dir validation), `find_case_path`, `get_field_value`.
**Signature:** `def find_case_path(cls, dir_path: Path, file_name: str, case_sensitive: bool) -> Path | None`
**Data Shape:** `secrets_dir` is one path or a sequence; per-field the value is the file's text content (string), later parsed by the shared complex/simple pipeline inherited from `PydanticBaseEnvSettingsSource`.

### Decisive source
```python
for field_key, env_name, value_is_complex in self._extract_field_info(field, field_name):
    # paths reversed to match the last-wins behaviour of `env_file`
    for secrets_path in reversed(self.secrets_paths):
        path = self.find_case_path(secrets_path, env_name, self.case_sensitive)
        ...
        if path.is_file():
            return path.read_text(encoding='utf-8').strip(), field_key, value_is_complex
```
Dir-validation ladder in `__call__`: missing directory → `warnings.warn(f'directory "{path}" does not exist')`
(no stacklevel, deliberately); all-missing → return `{}`; existing-but-not-a-directory →
`raise SettingsError(f'secrets_dir must reference a directory, not a {path_type_label(path)}')`.

**Flow:** Validate/collect dirs → run the inherited env-source `__call__` loop; for each field, candidate names come from `_extract_field_info` (aliases first), each tried against dirs in *reversed* list order so a later configured dir overrides an earlier one (matching dotenv multi-file last-wins). Case-insensitive mode matches lowercased filenames. A found non-file entry (symlink to dir, socket) warns and keeps scanning. Content is read explicitly as UTF-8 — never locale default — and `.strip()`ed.
**Invariant:** Missing dirs are warnings, not errors (secrets are optional by design); only an existing non-directory is fatal. Precedence: alias order first, then reversed dir order. Empty files yield `''` (not None) — which still counts as "found".
**Probe:** `python3 -m pytest tests/test_settings.py -k test_secrets_path_multiple -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`); `tests/test_settings.py:2049-2073`: with `_secrets_dir=(d1, d2)`, `foo2` resolves from `d2` — later dir wins; reversing the tuple flips the winner.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "secrets dir find_case_path read_text settings source", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the warn-skip / fatal-non-dir ladder, reversed-path last-wins scan, case-insensitive filename matching, and explicit-UTF-8 strip read. Adapt the warning channel and `path_type_label` wording to your host. Omit the `_init_state` warning-dedup plumbing unless your resolution also warns on incomplete FieldInfo definitions.
