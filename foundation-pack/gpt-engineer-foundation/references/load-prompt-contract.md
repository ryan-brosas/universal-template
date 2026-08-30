<!-- capsule-v2 -->
# load-prompt-contract — Which file/interactive inputs assemble a Prompt, and where does each malformed input fail?

**Source:** gpt-engineer MIT `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory `gpt-engineer`. **Question:** How do prompt file, interactive fallback, entrypoint prompt, and image directory combine into a `Prompt`, with what exact error/empty-input semantics?

## Prompt-assembly seam
**Path/Symbol:** `gpt_engineer/applications/cli/main.py:load_prompt` (:105-170) + `concatenate_paths` (:93-102); target type `gpt_engineer/core/prompt.py:Prompt` (:6-44).
**Signature:** `load_prompt(input_repo: DiskMemory, improve_mode: bool, prompt_file: str, image_directory: str, entrypoint_prompt_file: str = "") -> Prompt`; `Prompt(text: str, image_urls: Optional[Dict[str,str]] = None, entrypoint_prompt: str = "")`.
**Data Shape:** returns Prompt; failure mode is raised ValueError (directory prompt path, missing entrypoint file, empty image dir, non-dir image path); interactive `input()` when no usable prompt text.

### Decisive source
```python
prompt_str = input_repo.get(prompt_file)
if prompt_str:                       # TRUTHINESS gate — an EMPTY existing
    print(colored("Using prompt from file:", "green"), prompt_file)   # file still re-prompts!
    print(prompt_str)
else:
    if not improve_mode:
        prompt_str = input("\nWhat application do you want gpt-engineer to generate?\n")
    else:
        prompt_str = input("\nHow do you want to improve the application?\n")
...
if os.path.isdir(full_image_directory):
    if len(os.listdir(full_image_directory)) == 0:
        raise ValueError("The provided --image_directory is empty.")
    image_repo = DiskMemory(full_image_directory)
    return Prompt(prompt_str, image_repo.get(".").to_dict(), entrypoint_prompt=entrypoint_prompt)
```

**Flow:** reject directory-as-prompt-file → read via DiskMemory.get → truthy? announce+use : else ask interactively (question text switches on improve_mode) → entrypoint_prompt_file=="" ⇒ "" : resolve via concatenate_paths (if sub-path is inside base keep it verbatim; if outside, normpath(join(base,sub))) then must be an existing FILE else ValueError → image_directory=="" ⇒ images None : must be non-empty dir else ValueError; `DiskMemory(dir).get(".")` dict of files becomes `image_urls`. `Prompt.to_langchain_content()` later renders each image as `{"type":"image_url","image_url":{"url":...,"detail":"low"}}` prefixed by `Request:` text.
**Invariant:** (1) Existence is not enough — EMPTY prompt file falls through to interactive input (pinned by a dedicated test). (2) Image ingestion keys are FILE NAMES inside the directory; the dict lands on Prompt.image_urls verbatim. (3) concatenate_paths only rewrites paths that escape the project base — inside-base relative paths stay as-is so DiskMemory resolution is preserved. (4) All four malformed-input failures are loud ValueErrors BEFORE any LLM call. (5) Non-vision AI nulls image_urls downstream in main (:479-480) — assembly does not validate vision compatibility.
**Probe:** `tests/applications/cli/test_main.py` TestLoadPrompt ×5 — existing-file :198-212 (`result.image_urls is None`), no-file+generate :215-235 (interactive), directory-file :238-249 (`pytest.raises(ValueError)`), empty-file :252-273 (falls back to input despite existing file), image-directory :276-291 (`"mona_lisa.jpg" in result.image_urls`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "load_prompt image_directory entrypoint_prompt concatenate_paths ValueError", limit: 10 });
```

## Verdict
Adopt truthiness-gated file-or-interactive prompt loading with fail-loud validation before model calls; adapt the interactive questions/UX; omit the DiskMemory-specific `get(".")` bulk-read if your host has another FS abstraction (keep the empty-dir guard). Direct tests cover all five branches at pin.
