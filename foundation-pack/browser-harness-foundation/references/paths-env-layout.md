<!-- capsule-v2 -->
# Private-directory filesystem layout + env layering — where does per-user state go and who wins between files and real environment?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does a multi-instance CLI lay out config/runtime/tmp/workspace dirs and load .env defaults without ever clobbering operator environment?

## ensure_private_dir + setdefault env ladder
**Path/Symbol:** `src/browser_harness/paths.py:home_dir/ensure_private_dir/{config,runtime,tmp,workspace}_dir` (:9-49); loaders duplicated in `admin.py:107-125`, `daemon.py:13-31`, `helpers.py:19-36`.
**Signature:** `ensure_private_dir(path) -> Path` (mkdir parents; chmod 0o700 ONLY when freshly created); dir accessors read their env var first (`BH_CONFIG_DIR`, `BH_RUNTIME_DIR`, `BH_TMP_DIR`, `BH_AGENT_WORKSPACE`) falling back through `BH_HOME`/`BROWSER_HARNESS_HOME` → `XDG_CONFIG_HOME/browser-harness` → `~/.config/browser-harness`.
**Data Shape:** runtime default `<home>/runtime`, tmp `<home>/tmp`, workspace `<home>/agent-workspace`; `.env` parsed from repo root THEN workspace; `inspect_marker()` = `<config>/inspect-opened` (mtime doubles as the chrome://inspect reopen-TTL token).

### Decisive source
```python
def ensure_private_dir(path: Path) -> Path:
    existed = path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if not existed and sys.platform != "win32":
        os.chmod(path, 0o700)
    return path
...
k, v = line.split("=", 1)
os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
```

**Flow:** import time: both _ipc runtime+tmp dirs created eagerly so later joins never race creation; accessors resolve env override → expanduser+resolve → ensure_private_dir; .env loads at module import BEFORE constants like NAME/BROWSER_KIND derive.
**Invariant:** chmod fires ONLY on creation — re-chmodding an existing user dir would stomp operator intent; `setdefault` means the REAL environment ALWAYS wins over file values (a user-exported BU_CDP_URL can't be silently overridden by a stale .env); workspace file loading after repo file gives per-workspace precedence within the same mechanism; utf-8-sig decode tolerates BOM-written files.
**Probe:** No direct paths.py/loader unit test — coverage caveat; exercised transitively everywhere (`test_helpers._seed_skill` monkeypatches AGENT_WORKSPACE; endpoint tests patch `ipc._RUNTIME`). Anchors verified in source :19-24 and :116-122. Cross-repo echo: scout-foundation's env-persistence capsule records the identical real-env-wins rule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "private dir config runtime env setdefault", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt create-only chmod + env-ladder resolution + eager import-time mkdir + setdefault-only .env loading. Adapt variable names. Omit XDG fallback if your host mandates one root.
