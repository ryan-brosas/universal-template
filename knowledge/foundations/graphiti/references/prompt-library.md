<!-- capsule-v2 -->
# Prompt library & versioning — typed prompts as code + group-id fan-out decorator

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how are LLM prompts versioned like code, and how does one call fan out across multiple graph partitions?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/prompts/lib.py`: `PromptLibrary` (Protocol :47), `PromptLibraryImpl` (TypedDict :58), `VersionWrapper` (:69-79), `PromptTypeWrapper` (:80-85), `PromptLibraryWrapper` (:86+); prompt modules `extract_nodes.py` (`extract_message` :83, `extract_json` :213, `extract_text` :278, `classify_nodes` :347, `extract_attributes` :383, `extract_summary` :467, `extract_summaries_batch` :509), `dedupe_nodes/edges`, `summarize_nodes/sagas`; `decorators.py`: `handle_multiple_group_ids` (:29-118).
**Signature:** every prompt is `fn(context: dict) -> list[Message]`; the library exposes them as `library.extract_nodes.v1(context)` or by latest version — prompts are functions returning messages, never f-strings at call sites.
**Data Shape:** context dicts carry validated inputs; a prompt module maps one task → several source-type variants (message/json/text share extraction logic with per-type system text).

### Decisive source
```ts
class VersionWrapper:
    def __init__(self, func: PromptFunction): ...
    def __call__(self, context: dict[str, Any]) -> list[Message]: return self.func(context)
class PromptTypeWrapper:
    def __init__(self, versions: dict[str, PromptFunction]): ...   # 'v1' -> fn
# decorators.py
def handle_multiple_group_ids(func):
    async def wrapper(self, *args, **kwargs):
        # if group_ids has N entries: execute_for_group(gid) per partition,
        # gather results; single group_id runs once
```

**Flow:** call sites ask the library for a named prompt + version → wrapper resolves the function → context in, `list[Message]` out. New prompt versions register side-by-side so evaluation can A/B them. The `handle_multiple_group_ids` decorator transparently fans one API call into per-partition executions and merges results.
**Invariant:** no inline prompts at call sites (all via library, versioned); same task = same signature across source types; multi-group fan-out is invisible to callers.
**Probe:** `tests/` prompt tests (version resolution picks v1/latest; message/json/text variants produce valid Message lists; group fan-out splits and merges).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "PromptLibrary VersionWrapper handle_multiple_group_ids extract_message prompt versions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt prompts-as-versioned-functions behind a Protocol library + a group-fan-out decorator for partitioned graphs; adapt the version registry to host.
