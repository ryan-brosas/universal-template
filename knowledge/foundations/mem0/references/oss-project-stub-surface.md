<!-- capsule-v2 -->
# OSS project-stub surface — how does an SDK keep its API shape while refusing hosted-only operations?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mem0`. **Question:** what does `memory.project.update` do in the OSS package, and how do config-driven construction and dead branches behave?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_OSSProject` (:461-470) / `_AsyncOSSProject` (:472-481) stub classes, `_PROJECT_UPDATE_UNSUPPORTED_ERROR` (:457), `Memory.from_config` classmethod (:731-737), `_should_use_agent_memory_extraction` (:739-758, defined :2413 twin — ZERO call sites at this HEAD); hosted counterpart for contrast: `mem0/client/project.py BaseProject._validate_org_project/_prepare_params` (:75-108).
**Signature:** `_OSSProject.update(custom_instructions=None, custom_categories=None, multilingual=None, decay=None)` → always ValueError; `from_config(config_dict: Dict) -> Memory`.
**Data Shape:** stub exposes the hosted method NAME with the OSS refusal message; hosted Project requires org_id AND project_id as a PAIR (`_prepare_params` raises "Please provide both" on half-config).

### Decisive source
```python
_PROJECT_UPDATE_UNSUPPORTED_ERROR = "Project updates are not supported by the OSS Memory SDK."

class _OSSProject:
    def update(self, custom_instructions=None, custom_categories=None,
               multilingual=None, decay=None):
        if decay is True:
            raise ValueError(get_decay_feature_error_message("sync", "project.update", "decay"))
        raise ValueError(_PROJECT_UPDATE_UNSUPPORTED_ERROR)
```
```python
@classmethod
def from_config(cls, config_dict):
    try:
        config = MemoryConfig(**config_dict)      # pydantic validation FIRST
    except ValidationError as e:
        logger.error(f"Configuration validation error: {e}")
        raise                                     # re-raise ORIGINAL pydantic error, not a wrap
    return cls(config)

def _should_use_agent_memory_extraction(self, messages, metadata):
    # agent_id present AND any assistant-role message → agent extraction path
    return has_agent_id and has_assistant_messages   # ← no caller in main.py @ 8d5b7865
```

**Flow:** `memory.project` returns a fresh stub whose every update flavor refuses with a stable message (decay additionally gets its own feature-gate message BEFORE the generic refusal — ordering encodes that decay is a known-but-gated feature, not an unknown one); hosted clients instead validate the org/project pair up-front and thread both ids into every query string; `from_config` is the dict→pydantic→instance constructor used by integrations.
**Invariant:** API-shape preservation beats convenience — the OSS surface keeps `project.update` callable so integrations written against hosted don't AttributeError, but failure is LOUD and typed-by-message; `from_config` must re-raise the pydantic error unwrapped (integrations match on it); `_should_use_agent_memory_extraction` is DEAD CODE at this HEAD (defined sync+async, never called) — a porter should NOT wire it into add() thinking it's load-bearing; the real agent-extraction dispatch happens elsewhere (add() path mined in v3-phased-add).
**Probe:** no dedicated suite for the stubs or from_config at this HEAD — coverage caveat recorded; behavior pinned by reading all three raise sites + the hosted pair-validation tests under `tests/test_server_params.py` (imports Mem0ValidationError). Adversarial note: grep confirms zero `_should_use_agent_memory_extraction(` call sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "from_config _should_use_agent_memory_extraction _OSSProject", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: mnt-hdd-utopia-inspo-memory-mem0.mem0.memory.main.Memory.from_config Method mem0/memory/main.py 731-737)

## Verdict
Adopt the loud-refusal stub pattern for feature-gated surfaces and unwrapped pydantic re-raise in from_config; adapt messages to your product split; OMIT wiring the agent-extraction predicate — it is currently dead code, noted so a later HEAD that calls it gets re-mined.
