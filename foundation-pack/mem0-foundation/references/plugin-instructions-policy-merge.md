<!-- capsule-v2 -->
# Repo-carried extraction policy — how does a project steer what the memory layer extracts?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** how do you let a repository define its own memory-extraction policy that travels with checkout and team?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/_instructions.py`: `load_instructions` (:28-51); consumed by `auto_capture.store_exchange` via `body.update(load_instructions())` (:131).
**Signature:** `load_instructions(cwd=None) -> dict[str,str]` — keys present only when non-empty.
**Data Shape:** repo `mem0.md` sections: `## Instructions` → `custom_instructions`; `## Agent Instructions` → `agent_custom_instructions`.

### Decisive source
```python
try:
    config = load_full_config(cwd)
except Exception:
    return {}                        # no policy must never break a capture
out = {}
custom = config.get("instructions")
if isinstance(custom, str) and custom.strip():
    out["custom_instructions"] = custom.strip()
agent = config.get("agent_instructions")
if isinstance(agent, str) and agent.strip():
    out["agent_custom_instructions"] = agent.strip()
return out

# consumer merges VERBATIM into the add body:
body.update(load_instructions())
```

**Flow:** resolve cwd (arg → MEM0_CWD env → process cwd) → parse mem0.md → map prose sections to the platform's two instruction scopes → merge into every conversational write body.
**Invariant:** absent/partial policy adds ZERO keys; policy text passes through unmodified (platform owns interpretation); any parse failure degrades to "no policy", never to a failed write.
**Probe:** deterministic grep `grep -n "agent_custom_instructions" integrations/mem0-plugin/scripts/_instructions.py` + suite run `.venv/bin/python -m pytest integrations/mem0-plugin/tests -q -k instructions`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "load_instructions custom_instructions mem0.md", limit: 8, fields: ["name", "file"] });
```

## Verdict
Adopt repo-carried policy files merged verbatim into extraction requests (two scopes: user/project vs agent); adapt section names/format to your host; omit mem0's platform param names.
