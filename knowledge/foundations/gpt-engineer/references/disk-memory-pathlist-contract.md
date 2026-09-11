<!-- capsule-v2 -->
# disk-memory-pathlist-contract — How does DiskMemory double as KV store AND path-list provider, and what guards exist?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What are the traversal, image-encoding, traversal-guard, and log-append contracts of the file-backed memory?

## DiskMemory contract seam
**Path/Symbol:** `gpt_engineer/core/default/disk_memory.py` (__contains__ :64, __getitem__ :81-114 base64 images, __setitem__ guard :163-172, __iter__ :198-214 sorted relative paths, log() :288-320 timestamped append, archive_logs :321-329); `gpt_engineer/tools/supported_languages.py:SUPPORTED_LANGUAGES`.
**Signature:** dict-protocol class rooted at self.path; `log(key, val)` appends under `<root>/logs/<key>`.
**Data Shape:** Keys are RELATIVE path strings; iteration yields SORTED relative paths of all files recursively; .png/.jpeg/.jpg values read back as `data:<mime>;base64,...` strings.

### Decisive source
```python
# __setitem__ / log() shared guard:
if str(key).startswith("../"):
    raise ValueError(f"File name {key} attempted to access parent path.")
full_path.parent.mkdir(parents=True, exist_ok=True)

# __iter__ — deterministic order:
return iter(sorted(str(item.relative_to(self.path)) for item in sorted(self.path.rglob("*")) if item.is_file()))

# log() — timestamped append-only:
with open(full_path, "a", encoding="utf-8") as file:
    file.write(f"\n{datetime.now().isoformat()}\n")
    file.write(val + "\n")
```

**Flow:** constructor mkdir -p → standard KV ops → get() returns nested DiskMemory for DIRECTORIES (recursive namespace) or default on any error → log() prefixes ISO timestamp lines into logs/-subtree → archive_logs() moves logs/ to logs_<timestamp>/ at each run start.
**Invariant:** (1) Iteration is DOUBLE-sorted (rglob result sorted, then keys sorted) — deterministic prompt/log ordering across platforms; rely on it when diffing contexts. (2) Image values are DATA URLS not paths — feeding them straight into text prompts embeds megabytes; Prompt.to_langchain_content expects them as image_url parts. (3) The ../ guard exists ONLY on write paths (setitem/log) — READS via get()/getitem don't check, so treat memory keys as trusted input from internal flows only. (4) log() writes under `logs/` REGARDLESS of key shape (path join with logs dir) while archive rotates the whole dir pre-run — log filenames (all_output.txt, improve.txt, diff_errors.txt, debug_log_file.txt, gen_entrypoint_chat.txt) are the de-facto audit schema. (5) to_path_list_string(supported_only=True) filters via SUPPORTED_LANGUAGES extension union — the context-selection whitelist lives OUTSIDE this module.
**Probe:** `grep -c "startswith(\"../\")" gpt_engineer/core/default/disk_memory.py` → 2 (setitem + log).
**Probe:** `grep -n 'base64.b64encode' gpt_engineer/core/default/disk_memory.py` → :109 (image branch).
**Probe:** `tests/core/default/test_disk_file_repository.py` covers KV roundtrip incl directory-get semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "DiskMemory to_path_list_string archive_logs supported_files", limit: 10 });
```

## Verdict
Adopt sorted-iteration + timestamped-log + archive-rotate trio for reproducible agent workspaces; adapt the extension whitelist mechanism; add read-side path validation your threat model needs (upstream omits it deliberately).
