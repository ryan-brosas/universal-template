<!-- capsule-v2 -->
# Per-run task folder — why does importing config.py create directories, and what lands in them?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you give every agent run its own durable evidence folder without passing paths through every layer?

## Import-time monotonically-increasing task_N folder
**Path/Symbol:** `config.py` (repo root, whole file 22L); consumers `SOURCE_LOG_FOLDER_PATH` in openai_msg_parser (`ConversationStorage` default), get_dom_with_content_type (text_only_dom.txt writes); `PROJECT_SOURCE_ROOT` in ui_manager overlay path.
**Signature:** Module-level constants computed at import: `PROJECT_SOURCE_ROOT`, `BASE_LOG_FOLDER`, `SOURCE_LOG_FOLDER_PATH`, `PROJECT_ROOT`, `PROJECT_TEMP_PATH`.
**Data Shape:** `log_files/task_<N>/` where N = max existing task number + 1 (glob-scanned at import). Side effects at import: mkdir for both the task folder and `<root>/temp`.

### Decisive source
```python
existing_tasks = glob.glob(os.path.join(BASE_LOG_FOLDER, 'task_*'))
next_task_num = 1 if not existing_tasks else max([int(os.path.basename(t).split('_')[1]) for t in existing_tasks]) + 1
SOURCE_LOG_FOLDER_PATH = os.path.join(BASE_LOG_FOLDER, f'task_{next_task_num}')
...
if not os.path.exists(SOURCE_LOG_FOLDER_PATH):
    os.makedirs(SOURCE_LOG_FOLDER_PATH)
```
Everything evidence-shaped flows there WITHOUT explicit plumbing: raw + enriched accessibility trees (`json_accessibility_dom{,_enriched}.json`, aiofiles async writes), per-page text DOM dumps (`text_only_dom.txt`), and the unified conversation transcript (`task_conversation_<ts>.json`) — screenshots land in their own cwd-relative `screenshots/`, videos in `videos/`.
**Flow:** import config (any module) → folder minted once per process → ConversationStorage/DOM dumpers write into it by default.
**Invariant:** Import order defines your run's folder — two processes importing concurrently can race the glob and share N. The folder is created even for pure-library imports (side-effectful config is deliberate here so debug artifacts always have a home). PDF extraction uses a SEPARATE fixed temp file cleaned in finally — never the task folder.
**Probe:** No tests (coverage caveat). Graph pin: WRITES edges (53 in graph edge_types) concentrate on SOURCE_LOG_FOLDER_PATH consumers; `trace_path --function-name save_conversation --direction outbound` reaches json.dump under this path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "source log folder path task", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt import-time run folders only for single-process CLIs; adapt to explicit run-id injection for servers (this repo's own API mode would misbehave multi-worker). Omit the glob-max numbering under concurrency — use uuid or timestamped names instead.
