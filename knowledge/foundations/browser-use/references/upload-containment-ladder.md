<!-- capsule-v2 -->
# Upload file-path containment ladder — how does an LLM-chosen upload path get confined to trusted files without breaking remote browsers?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you stop `../` traversal and local/remote basename collisions when the agent picks which file to upload?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `upload_file` action (:860-1038), GHSA-j9hj-92j8-jv9h fix comment (:903-912), realpath defense-in-depth (:913-920).
**Signature:** `async def upload_file(params: UploadFileAction, browser_session, available_file_paths: list[str], file_system: FileSystem)`.

### Decisive source
```python
if params.path not in available_file_paths:
    if params.path not in browser_session.downloaded_files:
        # Only rewrite to the local FileSystem path on LOCAL sessions — on remote
        # sessions params.path addresses a file on the REMOTE machine, and a
        # coincidental basename collision (/tmp/note.md vs local note.md) must not
        # silently upload the local file.
        if browser_session.is_local and file_system and file_system.get_dir():
            file_obj = file_system.get_file(params.path)   # matches by BASENAME
            if file_obj:
                # Build from FileSystem-owned basename (file_obj.full_name), NOT from
                # params.path: get_file() matches by basename so '../../../note.md'
                # would otherwise resolve to a sibling outside data_dir. GHSA-j9hj-92j8-jv9h.
                file_system_path = str(file_system.get_dir() / file_obj.full_name)
                real_path = os.path.realpath(file_system_path)
                real_dir = os.path.realpath(str(file_system.get_dir()))
                if not (real_path == real_dir or real_path.startswith(real_dir + os.sep)):
                    return ActionResult(error=f'Upload of {params.path!r} escapes FileSystem directory; refusing.')
                params = UploadFileAction(index=params.index, path=file_system_path)
# Local-only existence + non-empty checks follow (0-byte file => explicit error).
```

**Flow:** allowlist (`available_file_paths`) → session downloads → (local only) FileSystem basename match → rebuild path from the OWNED basename (never from agent text) → realpath prefix containment check → rewrite params → dispatch UploadFileEvent. Remote sessions skip the local rewrite entirely and pass absolute remote paths through.
**Invariant:** never join agent-controlled path text onto a directory (basename match first, owned-name rebuild second); realpath containment is the backstop that survives symlinked dirs; the local-vs-remote branch must be decided by `is_local` BEFORE any basename logic or you exfiltrate local files to remote uploads.
**Probe:** `tests/ci/security/test_upload_file_containment.py` — `test_traversal_in_agent_path_does_not_escape_filesystem_dir` (:62), `test_traversal_with_no_basename_match_still_fails_safely` (:114), `test_remote_session_does_not_rewrite_to_local_filesystem_on_basename_collision` (:145).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "upload_file available_file_paths file_input GHSA containment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier admission ladder + owned-basename rebuild + realpath containment; adapt the FileSystem service; omit the file-input proximity heuristics if your host has direct DOM handles.
