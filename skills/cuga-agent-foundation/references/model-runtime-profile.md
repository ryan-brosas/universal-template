<!-- capsule-v2 -->
# Model-keyed runtime config defaults — how do you ship model-specific settings that TOML can't anticipate, with a clean three-source precedence?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Some models need different agent defaults (e.g. gpt-oss-20b needs few-shots on and a restricted bind list) regardless of user config — where do per-model defaults sit in the precedence ladder, and how do you match provider-prefixed names?

## configurable > model-profile > settings; normalize `openai/gpt-oss-20b` AND Ollama `gpt-oss:20b` to one key
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/model_runtime_profile.py` — `GPT_OSS_20B_ID` :7 + `GPT_OSS_20B_RUNTIME_DEFAULTS` :9-14 (few_shots True, bind mode "apps", apps `[knowledge, filesystem]`, include find_tools), `_normalized_model_key` :17-23 (`rsplit("/", 1)[-1]` then `replace(":", "-")`), `runtime_defaults_for_model` :26-32 ({} for unknown/empty — never partial), `resolved_runtime_model_name` :35-46 (`model_name` or `model` attr from configurable-llm first, graph default second), `resolve_bind_tools_fields` :75-116.
**Signature:** `resolve_bind_tools_fields(configurable, model_name, *, settings_mode_fn, settings_apps_fn, settings_tool_names_fn, settings_include_fn) -> tuple[mode:str, apps:list[str], tool_names:list[str], include_find_tools:bool]`.
**Data Shape:** per-key ladder — strings: None/"" falls through; lists: None **OR []** falls through; bools: only None falls through. Settings injected as CALLABLES so the module has no import-time coupling to live config.

### Decisive source
```python
# :17-23 — the normalization contract
# openai/gpt-oss-20b and Ollama's gpt-oss:20b both match gpt-oss-20b
s = model_name.strip().lower()
if "/" in s: s = s.rsplit("/", 1)[-1].strip()
return s.replace(":", "-")
# :96-100 — empty-list is "unset" for list keys (else a user's [] could never reset)
apps_raw = cfg.get("cuga_lite_bind_tools_apps")
if apps_raw is None or apps_raw == []:
    apps_raw = prof.get("cuga_lite_bind_tools_apps")
if apps_raw is None or apps_raw == []:
    apps_raw = settings_apps_fn()
```
**Flow:** resolve the effective model name (configurable LLM object wins over graph default; reads `.model_name`/`.model`) → exact-match against profile table after normalization → build per-field values walking configurable → profile → settings-callables → coerce bools from strings ("true/1/yes/on") and normalize string-lists (single string ⇒ 1-element list).
**Invariant:** (1) Unknown models get `{}` — profiles are purely additive, never a baseline. (2) The `[]`-as-unset rule exists because an explicit empty list must still be distinguishable from absence at each layer. (3) Profile defaults are DICT-COPIED (`dict(...)`) on return — callers mutating them must not corrupt the table.

**Probe:** No direct unit suite at HEAD for this module (coverage caveat — pure-function file, source-read verified; consumed by prepare-node binding path pinned via test_arguments.py / test_prepare_node_weak_schema_tools.py at the integration layer).
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "runtime_defaults_for_model resolve_bind_tools_fields normalized_model_key", limit: 8 });
```
## Verdict
Adopt for any agent whose optimal defaults vary by model family; keep profiles additive + dict-copied + normalized-key matched. Adapt the key set to your config surface.
