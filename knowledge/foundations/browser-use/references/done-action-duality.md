<!-- capsule-v2 -->
# Done action duality — structured vs free-text completion and the attachments contract

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does task completion differ when an output_model is configured, and which files attach to the final result?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `_register_done_action` (:2022-2124): structured branch (:2025), free-text branch (:2067); `use_structured_output_action` (:2126).
**Signature:** `param_model=StructuredOutputAction[output_model]` (Generic pydantic) vs `DoneAction`.

### Decisive source
```python
# STRUCTURED branch: enums serialize at ALL nesting levels only via mode='json'
output_dict = params.data.model_dump(mode='json')
attachments = []
for file_name in params.files_to_display or []:
    if file_system.display_file(file_name):
        attachments.append(str(file_system.get_dir() / file_name))
# Auto-attach ACTUAL session downloads (CDP-tracked) but NOT user whitelist paths:
session_downloads = browser_session.downloaded_files
existing = set(attachments)
for file_path in session_downloads:
    if file_path not in existing: attachments.append(file_path)
return ActionResult(is_done=True, success=params.success,
                    extracted_content=json.dumps(output_dict, ensure_ascii=False), ...)

# FREE-TEXT branch: display_files_in_done_text flag decides whether file CONTENT
# is inlined into the message (with 'Attachments:' header) or silently attached;
# memory truncates to 100 chars + '- N more characters'.
```

**Flow:** constructor picks the branch from `output_model` (re-registrable later via use_structured_output_action, which deletes nothing — done is re-registered over itself by name) → structured path guarantees machine-parseable JSON as extracted_content with is_done/success flags → both paths union requested files with session downloads, deduped by absolute path.
**Invariant:** `model_dump(mode='json')` is mandatory for nested enums (plain dump emits non-JSON enum objects); auto-attach covers ONLY CDP-tracked downloads — adding available_file_paths whitelist files would leak user files into results; dedupe runs on resolved absolute paths.
**Probe:** deterministic citation :2022-:2124; end-to-end covered by agent-level tests (`tests/ci/test_agent_planning.py` uses done paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "_register_done_action StructuredOutputAction files_to_display downloaded_files attachments", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-branch registration pattern + mode='json' serialization rule + downloads-only auto-attach; adapt attachment semantics; omit display_files_in_done_text if your UI always wants inline content.
