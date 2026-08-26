<!-- capsule-v2 -->
# Managed-value injection — How does run-progress state enter schemas without becoming durable?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** How can a schema expose computed values like `RemainingSteps` that nodes read but checkpoints never store?

## Managed specs are classes computing from the scratchpad at input-prep time
**Path/Symbol:** `libs/langgraph/langgraph/managed/base.py:ManagedValue/ManagedValueSpec/is_managed_value` (:18-28), implementations `libs/langgraph/langgraph/managed/is_last_step.py` (:9-23), resolution arm `libs/langgraph/langgraph/pregel/_algo.py:_proc_input` (:1369-1370), compile-side recognition `libs/langgraph/langgraph/graph/state.py:_is_field_managed_value` (:1925-1943, cross-ref state-schema-compilation capsule).
**Signature:** `class ManagedValue(ABC, Generic[V]): @staticmethod @abstractmethod get(scratchpad: PregelScratchpad) -> V`; `ManagedValueSpec = type[ManagedValue]`; usage `Annotated[int, RemainingStepsManager]`.
**Data Shape:** `ManagedValueMapping = dict[str, ManagedValueSpec]` lives beside channels in task prep; a schema field annotated with a ManagedValue subclass is recognized into `graph.managed` instead of creating a channel.

### Decisive source
```python
class IsLastStepManager(ManagedValue[bool]):
    @staticmethod
    def get(scratchpad: PregelScratchpad) -> bool:
        return scratchpad.step == scratchpad.stop - 1

IsLastStep = Annotated[bool, IsLastStepManager]

class RemainingStepsManager(ManagedValue[int]):
    @staticmethod
    def get(scratchpad: PregelScratchpad) -> int:
        return scratchpad.stop - scratchpad.step

RemainingSteps = Annotated[int, RemainingStepsManager]
```
```python
# _proc_input — managed arm fires ONLY when the key is not a real channel:
            else:
                val[chan] = managed[chan].get(scratchpad)
```

**Flow:** Compile: `_get_channels` routes `Annotated[T, SomeManagedValueSubclass]` fields into the `managed` mapping (excluded from root schemas where disallowed). Runtime: when a node subscribes to such a key, input projection finds no channel of that name and calls the spec's static `get(scratchpad)` — recomputed per task from the run's progress counters (`step`, recursion-limit `stop`). Nothing is written back; nothing enters checkpoint blobs; replaying a checkpoint recomputes identical values because they derive from step position alone.
**Invariant:** Managed values must be PURE FUNCTIONS OF THE SCRATCHPAD — any dependence on external mutable state would desynchronize replays. They are read-only from the node's perspective and cost zero checkpoint bytes; the pattern exists precisely to expose run metadata (recursion-limit countdown, last-step flags) without inventing durable channels.
**Probe:** `python -m pytest tests/test_managed_values.py::test_managed_values_recognized -q` (Plain/NotRequired/Required annotations all land in graph.managed); inline: a graph whose state declares `remaining_steps: RemainingSteps` streams decreasing countdowns across steps while its checkpoint contains no such channel.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "managed value RemainingSteps is_managed_value", limit: 8 });
```

## Verdict
Adopt class-as-spec managed values for run-scoped computed state — it keeps progress metadata out of durability entirely. Adapt the annotation syntax to your host's schema system and inject whatever scratchpad your loop already tracks. Omit nothing here; the whole mechanism is six lines plus one resolution arm.