<!-- capsule-v2 -->
# Registry-gated deserialization — how do from_dict/from_folder avoid arbitrary code execution?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** Agents and models are restored from JSON (Hub Spaces!) — what prevents a malicious `class` field from instantiating attacker code via importlib, and which legacy migrations run at load?

## Closed allowlist registries
**Path/Symbol:** `src/smolagents/agents.py:AGENT_REGISTRY` (:1806-1813), `MultiStepAgent.from_dict` (:1010-1062), `from_folder` (:1118-1158), `from_hub` trust gate (:1097-1100); `src/smolagents/models.py:MODEL_REGISTRY` (:2066-2080); rename shim :1129-1134.
**Signature:** `AGENT_REGISTRY = {"ToolCallingAgent": ToolCallingAgent, "CodeAgent": CodeAgent}`; `MODEL_REGISTRY` pins 9 model classes; `from_hub(repo_id, ..., trust_remote_code=False)` raises without explicit opt-in.
**Data Shape:** agent.json carries class names + tool CODE strings; folder layout tools/{name}.py + managed_agents/{name}/ recursive.

### Decisive source
```python
# :1806-1809 — the comment is the threat model:
# Agent Registry for secure deserialization
# Only classes listed here can be instantiated during deserialization (from_dict/from_folder).
# This prevents arbitrary code execution via importlib-based dynamic loading.
model_class = MODEL_REGISTRY.get(model_info["class"])
if model_class is None:
    raise ValueError(f"Unknown model class '{model_info['class']}'. Supported models: ...")
# :1129-1134 — silent legacy migration at load:
if agent_dict.get("model", {}).get("class") == "HfApiModel":
    agent_dict["model"]["class"] = "InferenceClientModel"
```

**Flow:** Load path resolves BOTH agent and model classes through registries — unknown names are loud ValueErrors listing the closed set, never dynamic imports. Tools are different by design: they ARE code (`Tool.from_code` execs the file) so they're gated one level up by `trust_remote_code=True` on every Hub entry point (tool and agent). `from_folder` recursively restores managed agents, applies the HfApiModel→InferenceClientModel rename with a warning, then defers to `from_dict`, whose kwargs merge order is dict-values → None-filter → user-kwargs override. Serialization's counterpart scrubbing lives in `Model.to_dict`: token/api_key attributes print an explicit refusal instead of exporting.
**Invariant:** Registries must enumerate EVERY instantiable class explicitly; adding a new agent/model class without registry entry breaks round-trips (fail-closed, not fail-open). The trust flag gates code-bearing payloads only — structural JSON stays ungated.
**Probe:** `tests/test_agents.py::test_from_dict_invalid_model_class/:test_from_dict_invalid_agent_class` (:1597-1645), `test_from_folder` parametrized legacy dicts (:2251+), `test_from_dict` roundtrip (:1496). Live: `from_dict({"model":{"class":"Evil"}, ...})` → ValueError naming supported set.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "AGENT_REGISTRY MODEL_REGISTRY from_dict from_folder", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt allowlist registries + fail-closed unknown-class errors for any JSON-borne deserialization. Adapt the rename-shim list as your classes evolve. Omit the secret-scrub print in to_dict and users will leak keys into pushed Spaces.
