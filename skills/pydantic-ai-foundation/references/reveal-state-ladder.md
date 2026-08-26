<!-- capsule-v2 -->
# Reveal-state availability ladder — given raw history evidence, when is a deferred tool actually callable right now?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What exact predicate decides "this tool is available to the model on this turn", covering always-visible, discovered, capability-owned, and already-dispatched calls?

## `RunContext.is_tool_available` + `AnchoredEvidence`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_run_context.py:is_tool_available` (:342–404), `AnchoredEvidence` (:38–57), `_anchored_evidence` field (:254–260), `_deferred_capability_ids` (:312–322), `available_capability_ids` (:289–310), `discovered_tool_names` doc (:242–252).
**Signature:** `is_tool_available(self, tool: str | ToolDefinition) -> bool`.
**Data Shape:** Inputs: `tool_def.defer_loading`, `tool_def.with_native`, `tool_def.capability_id`; run state `capabilities` registry, `loaded_capability_ids` (history-derived before each request), `discovered_tool_names` (raw evidence set); private `AnchoredEvidence(discovered_tool_names, loaded_capability_ids)` widened sets stamped at tool-call dispatch.

### Decisive source
```python
# _run_context.py:373-404 — the ladder, condensed
if tool_def.with_native != ToolSearchTool.kind and not tool_def.defer_loading:
    return True                                   # always-available (checks defer_loading,
                                                  #  not just with_native: stamping may lag)
capability_id = tool_def.capability_id
# Capability-owned: the LOAD is the reveal — demanding a separate marker strands
# the tool forever (history processing can drop the reveal but keep the load;
# reloading an active capability is refused).
if (capability_id is not None
        and capability_id in self._deferred_capability_ids          # still CONFIGURED deferred
        and capability_id in self.loaded_capability_ids | evidence.loaded_capability_ids):
    return capability_id in self.available_capability_ids | evidence.loaded_capability_ids
if tool_def.name not in self.discovered_tool_names | evidence.discovered_tool_names:
    return False                                    # never revealed
return capability_id is None or capability_id in (
    self.available_capability_ids | evidence.loaded_capability_ids)
```

**Flow:** definition-form evaluates the def's own fields against history-recorded reveal state (reliable even when a wrapper removed it from the resolved set); name-form looks up live `tools` first, falling back to `available_tool_names` mid-resolution or inside Temporal activities; unknown name → False.

**Invariant:** `discovered_tool_names` is RAW EVIDENCE, not a verdict — it collects every name any search/delta/load mentioned without checking existence or ownership; both halves of the capability check are load-bearing (configured-deferred TODAY, not merely named by a stale load record). The anchored-evidence widening exists because a boundary another provider would skip on the wire hid nothing from the provider that ALREADY made the call — future-request views use the conservative window; dispatch-time checks use the widened one. Additive widening only: the base sets are shared mutable state written in-step.

**Probe:** `tests/test_capabilities.py::test_run_context_is_tool_available` (:5031 — every reveal path × both argument forms incl. unloaded-capability denial), `test_run_context_is_tool_available_falls_back_while_tools_unresolved` (:4962), `tests/test_capabilities.py:4306` (visibility snapshot across hook timing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "is_tool_available AnchoredEvidence discovered_tool_names loaded_capability_ids available_capability_ids", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (always-visible → capability-load-as-reveal → undiscovered-denial → owner-loaded check) and the raw-evidence vs verdict distinction; adopt the additive AnchoredEvidence pattern wherever one consumer needs a wider window than the conservative shared state. Adapt the Temporal/activity fallbacks to your durable runtime. Omit nothing.
