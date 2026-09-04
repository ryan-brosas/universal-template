<!-- capsule-v2 -->
# ACP tool-call presentation — how do you render rich editor tool-call cards (kind/locations/diff) without lying about unrecognized tools?

**Source:** pydantic-ai-harness (MIT) `main@76db3dec`; Codebase Memory `pydantic-ai-harness`. **Question:** How should a protocol adapter decorate tool calls with rich presentation fields while guaranteeing malformed or foreign tool calls fall back to generic rendering and never expose workspace-escaping paths?

## Name-keyed presenter registry with arg-shape validation
**Path/Symbol:** `pydantic_ai_harness/experimental/acp/_presentation.py:ToolCallPresentation` (:30–43), `_HANDLERS` (:136–149), `default_coding_presenter` (:152–163), `chain_presenters` (:166–182), `absolutize`/`_resolve_within` (:185–218).
**Signature:** `ToolCallPresenter = Callable[[ToolCallPart], ToolCallPresentation | None]`; `chain_presenters(*presenters) -> ToolCallPresenter`; `absolutize(presentation, cwd) -> ToolCallPresentation`.
**Data Shape:** Frozen dataclass of all-optional fields (`kind`, `title`, `locations: tuple[...] = ()`, `content: tuple[...] = ()`). Registry maps ~12 FileSystem/Shell tool names → per-tool handlers that validate argument shape and return `None` on mismatch.

### Decisive source
```python
def default_coding_presenter(call: ToolCallPart) -> ToolCallPresentation | None:
    handler = _HANDLERS.get(call.tool_name)
    if handler is None:
        return None
    # Malformed arguments surface from `args_as_dict` as a sentinel dict no handler matches.
    return handler(call.args_as_dict())

def _resolve_within(path: str, cwd: str) -> str | None:
    """Resolve a relative `path` against `cwd`, or `None` if it escapes it."""
    if os.path.isabs(path):
        return path
    resolved = os.path.normpath(os.path.join(cwd, path))
    relative = os.path.relpath(resolved, os.path.normpath(cwd))
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return None
    return resolved
```

**Flow:** tool-call start (or permission request) → adapter calls the configured presenter → first non-`None` presentation in the chain wins (`None` = "I don't handle this") → adapter defaults title to the tool name and kind to its own default when the presentation omits them → `absolutize(presentation, cwd)` resolves relative paths against the session cwd before sending; locations or file-edit diffs whose resolved path escapes cwd are **dropped entirely**, not clamped. Empty strings are legitimate for content text (`new_text=''` deletes a snippet; `content=''` writes an empty file) but not for identity fields like `path`. `list_directory` is matched by name alone — its only argument is optional, so no shape check exists (documented exception).
**Invariant:** Unrecognized or malformed calls produce `None`, so the client gets generic rendering instead of fabricated fields; an editor is never shown a click-to-file link or diff outside the session workspace; coupling is by tool *name*, so renaming those capabilities silently degrades to generic rendering rather than erroring.
**Probe:** `tests/experimental/acp/test_acp.py` `TestPresenterArgValidation` (:2115–2150), `TestPresenterComposition` (:2153–2167), `TestPathAbsolutization` (:2170–2207 — traversal escaping drops location AND diff), `TestToolCallPresentationIntegration` (:2043–2112 — permission request uses presenter kind, not hardcoded `execute`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "tool call presentation presenter chain absolutize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the presenter-as-predicate contract (`None` means fall back), the frozen all-optional presentation record, chain-first-match composition, and drop-don't-clamp path absolutization. Adapt the recognized-tool table to your capability's tool names. Omit the ACP diff/location schema shapes.
