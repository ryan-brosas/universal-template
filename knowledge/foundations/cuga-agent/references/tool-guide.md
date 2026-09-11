<!-- capsule-v2 -->
# Tool Guide Enrichment — append policy markdown to tool descriptions without poisoning cached tools across turns

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you enrich tool descriptions from multiple matched policies per turn, when the underlying tool objects are cached and reused across invocations?

## Deep-copy, multi-guide merge, runtime_tools app scope
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/enactment.py:660-782` (`PolicyEnactment.apply_tool_guide`); metadata production at `_merge_guide_metadata` :236-273 and `_enact_tool_guide` :599-626; matching in `agent.py:1236-1289` (`check_tool_guide_policies`).

**Signature:** `apply_tool_guide(tools: list, metadata: Optional[Dict[str, Any]]) -> list`.

**Data Shape:** Metadata `guides: [{policy_id, policy_name, guide_content, target_tools: [..|"*"], target_apps: [..]|None, prepend: bool, priority, ...}]` sorted by priority desc before application; legacy single-guide shape (`policy_type=="tool_guide"` + flat `guide_content`) still honored.

### Decisive source
```python
# enactment.py:667-697 — the reason for the copies, verbatim then code
# IMPORTANT: This method creates copies of tools before enriching to avoid
# modifying cached tool objects that might be reused across turns.
...
# Create copies of tools to avoid modifying cached originals
# This prevents guides from accumulating when tools are reused across turns
enriched_tools = [deepcopy(tool) for tool in tools]
```
App-scope rule (from ToolGuide model docstring `models.py:254-260`, enforced by the runtime filter):
> "Directly provided LangChain/runtime tools use the app name 'runtime_tools', so scoped policies for those tools must include it."

**Flow:** guides match independently (multiple allowed) → `_merge_guide_metadata` sorts priority-desc → at prompt/tool-prep time each tool is tested: `"*" in target_tools or tool.name in target_tools` OR `tool.metadata["app_name"] in target_apps` → description becomes `f"{content}\n\n{original}"` (prepend) or `f"{original}\n\n{content}"` (append).

**Invariant:** Two traps. (1) Never mutate the input list's objects — enrichment must re-apply fresh each turn on copies or guides accumulate forever on cached tools. (2) Known latent bug preserved for porters: the LEGACY branch (:782) builds `enriched_tools` copies but returns **the original `tools` list** — so under the legacy single-guide format the enrichment silently never reaches the caller. The new multi-guide path (:741) returns `enriched_tools` correctly. If you port only the legacy shape, you inherit a no-op.

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_e2e_tool_enrichment.py` (full-graph: enriched descriptions reach the model and change tool selection). Caveat: no direct unit test pins the deepcopy-vs-original return difference — that asymmetry was found by reading both branches at HEAD; verify with a two-turn cache test after porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "apply_tool_guide deepcopy enrich description", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copy-on-enrich with priority-sorted multi-guide merging and an explicit virtual app name for directly provided tools; fix (don't copy) the legacy-path return bug. Adapt matching fields (name/app) to your registry. Omit prepend mode if your models ignore leading description text.
