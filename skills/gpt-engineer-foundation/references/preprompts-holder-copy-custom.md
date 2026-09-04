<!-- capsule-v2 -->
# preprompts-holder-copy-custom — How are customizable prompts shipped safely?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** How does the custom-preprompts flow seed a project without clobbering user edits?

## Preprompt provisioning seam
**Path/Symbol:** `gpt_engineer/applications/cli/main.py:get_preprompts_path` (:173-200); loader `gpt_engineer/core/preprompts_holder.py:PrepromptsHolder.get_preprompts` (:27-30); source-of-truth `PREPROMPTS_PATH = Path(__file__).parent.parent.parent / "preprompts"` (paths.py:52).
**Signature:** `get_preprompts_path(use_custom_preprompts: bool, input_path: Path) -> Path`.
**Data Shape:** Nine preprompt files: clarify, entrypoint, file_format, file_format_diff, file_format_fix, generate, improve, philosophy, roadmap — loaded wholesale as {stem: content}.

### Decisive source
```python
original_preprompts_path = PREPROMPTS_PATH          # package-relative, survives wheel installs
if not use_custom_preprompts:
    return original_preprompts_path
custom_preprompts_path = input_path / "preprompts"
if not custom_preprompts_path.exists():
    custom_preprompts_path.mkdir()
for file in original_preprompts_path.glob("*"):
    if not (custom_preprompts_path / file.name).exists():   # NEVER overwrite existing customs
        (custom_preprompts_path / file.name).write_text(file.read_text())
return custom_preprompts_path
```
```python
# PrepromptsHolder: every file becomes a key
preprompts_repo = DiskMemory(self.preprompts_path)
return {file_name: preprompts_repo[file_name] for file_name in preprompts_repo}
```

**Flow:** flag off ⇒ package defaults; flag on ⇒ mkdir project/preprompts → copy each MISSING default in (first-write-wins) → holder reads ALL files from that dir.
**Invariant:** (1) Copy-if-absent means upstream updates never stomp user-tuned prompts, but ALSO means new upstream preprompts appear while deleted-by-user ones resurrect — regeneration is opt-in via rm. (2) Holder loads EVERYTHING in the dir: stray files become phantom prompt keys (harmless unless names collide with reserved: roadmap/generate/improve/philosophy/file_format*/clarify/entrypoint). (3) PREPROMPTS_PATH derives from `__file__` — works installed or vendored; do not replace with cwd-relative paths. (4) file_format_fix exists for chat-fix loops (used by legacy flows) though current steps.py doesn't import it — dead-ish asset kept for compat.
**Probe:** `ls gpt_engineer/preprompts | wc -l` → 9.
**Probe:** `grep -n 'exists()' gpt_engineer/applications/cli/main.py | head -3` → :194 dir check, :198 per-file skip-if-exists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "get_preprompts_path PrepromptsHolder PREPROMPTS_PATH custom", limit: 10 });
```

## Verdict
Adopt copy-if-absent provisioning + package-relative template root for any prompt-pack system; adapt file inventory; warn users that the preprompts dir is load-everything.
