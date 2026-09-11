<!-- capsule-v2 -->
# Agent filesystem — in-memory typed files with serializable state + device-code auth

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an agent get a safe scratch filesystem (typed files, state snapshots, LLM-friendly errors) and how does CLI auth use the OAuth device flow?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/filesystem/file_system.py` (941 lines): `FileSystemError` (:79, "shown to LLM"), `BaseFile` (ABC :85-142: `extension` abstract, write/append/sync_to_disk via ThreadPoolExecutor), typed subclasses (`MarkdownFile` :144, `TxtFile`, ...), `FileSystemState` (:345 — serializable `{files, base_dir, extracted_content_count}`), `FileSystem` (:353, in-memory dict + default files + sync); `sync/auth.py`: `get_or_create_device_id` (:22), `DeviceAuthClient.poll_for_token` (:157-273) implementing RFC 8628.
**Signature:** agent tools operate on in-memory `BaseFile` objects; disk is an explicit `sync_to_disk` step; `save_file_system_state()`/restore round-trips through `FileSystemState`.
**Data Shape:** files live as `{full_name -> BaseFile}` in memory; state export = plain dicts; auth persists via `CloudAuthConfig.load_from_file/save_to_file`.

### Decisive source
```ts
class FileSystemError(Exception):
    """Custom exception for file system operations that should be shown to LLM"""
# BaseFile: content mutated in memory first; disk write is offloaded:
async def sync_to_disk(self, path):
    with ThreadPoolExecutor() as executor:
        await asyncio.get_event_loop().run_in_executor(executor,
            lambda: file_path.write_text(self.content, encoding='utf-8'))
# RFC 8628 device flow with server-directed pacing:
if data.get('error') == 'authorization_pending':
    await asyncio.sleep(interval); continue
if data.get('error') == 'slow_down':
    interval = data.get('interval', interval * 2)   # honor server interval
    await asyncio.sleep(interval); continue
if 'access_token' in data: return data
```

**Flow:** agent file tools read/write the in-memory store (fast, deterministic for tests) → explicit sync flushes to disk off the event loop → whole filesystem snapshots into `FileSystemState` so runs resume with files intact. File errors raise a dedicated exception type that the tool layer surfaces to the model verbatim. Device auth: request code → show URL → poll respecting `authorization_pending`/`slow_down` (server-controlled interval) → persist token locally.
**Invariant:** memory-first mutation keeps tool results instant and replayable; disk I/O never blocks the loop; errors meant for the model are a distinct type; OAuth polling honors server pacing (`slow_down` doubles/overrides interval).
**Probe:** `tests/` filesystem tests (write→sync round-trip; state save/restore; error message surfaced); auth tests (pending/slow_down handling).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "FileSystem BaseFile FileSystemState sync_to_disk DeviceAuthClient poll_for_token", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt memory-first typed files + explicit snapshotting for agent scratch space; adopt RFC 8628 device flow verbatim for CLI auth. Adapt file types to host.
