<!-- capsule-v2 -->
# Auth private-storage lifecycle — how do you store an API key on disk so it is never world-readable, never half-written, and never silently ignored?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What does a safe single-file credential lifecycle look like when the file may be missing, corrupt, partially populated, or shared with foreign keys?

## Private-mode atomic writes + key-scoped clear + corrupt-file fail-loud
**Path/Symbol:** `src/browser_harness/auth.py:auth_path/load_auth_file/save_auth_record/clear_auth/auth_status` (:126-196), `_write_private_json` (:465-477), `_chmod_private` (:480-485); storage shape from `AuthRecord.to_storage` (:107-115).
**Signature:** `save_auth_record(record: AuthRecord, path=None)`; `clear_auth(path=None) -> bool`; `load_auth_file(path=None) -> dict`; `auth_status() -> {status, source, path}`; `_chmod_private(path, *, directory=False)`.
**Data Shape:** one JSON file (default `<config_dir>/auth.json`, overridable via `BH_AUTH_PATH`) holding namespaced records under `"browser_use"`; env var `BROWSER_USE_API_KEY` always wins over stored.

### Decisive source
```python
fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)   # file born 0600, not chmod-later
...
tmp = path.with_name(path.name + ".tmp")
_write_private_json(tmp, existing)
os.replace(tmp, path)
_chmod_private(path)
```
```python
existed = bool(data.get("browser_use"))
data.pop("browser_use", None)
if data: ... os.replace(tmp, path)      # foreign keys survive
else: path.unlink()                      # last key out removes the file
```

**Flow:** Save: mkdir parents → chmod dir 0700 → merge record into existing JSON under the `browser_use` namespace → write `.tmp` with O_CREAT+mode 0600 → atomic `os.replace` → re-chmod. Load: FileNotFoundError → `{}` (first-run is not an error), corrupt JSON/Unicode → raise `AuthError` naming the path (never silently `{}`). Clear: returns whether a record existed; pops only the namespace; keeps the file if foreign keys remain, unlinks otherwise. Status tri-sources: env → `"authenticated"/"env"`, stored-with-key → `"stored"`, else `"missing"` — doctor renders this instead of guessing.
**Invariant:** Credentials are created private (`0600` file / `0700` dir at birth via open-modes, best-effort chmod as belt-and-braces — `_chmod_private` swallows OSError), replaced atomically (no torn reads), namespaced (clear must not delete cohabitants), and ambiguity fails LOUD (corrupt auth raises; it is never treated as "logged out"). `_chmod_private` is best-effort because some filesystems reject modes — permission failure must not break login.
**Probe:** Executed against pinned source with `BH_AUTH_PATH` override: save → file mode `0o600`, dir `0o700`; status → `authenticated/stored` (env unset); clear #1 → `True`, file unlinked; clear #2 with foreign key → `True`, residual file keeps `other`; corrupt file → `AuthError("auth file is not valid JSON: …")`. No direct unit test covers this lifecycle — only indirect consumption at `tests/unit/test_admin.py:267` (doctor monkeypatches `auth_status` to throw AuthError) — coverage caveat; anchors verified at source :126-196, :465-485.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "browser-harness", qualified_name: "browser-harness.src.browser_harness.auth._write_private_json" });
```

## Verdict
Adopt open-with-mode private writes + os.replace atomicity, namespace-scoped clear with last-key-out unlink, and the loud AuthError for corrupt state. Adapt the env-var precedence order and BH_AUTH_PATH-style override to your host. Omit the OAuth/PKCE acquisition flows (see `auth-cli-dual-audience`) when you only need the storage contract.
