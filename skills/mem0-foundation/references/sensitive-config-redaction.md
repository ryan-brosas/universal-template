<!-- capsule-v2 -->
# Sensitive-field redaction — how do you deepcopy a config for telemetry without leaking secrets or dropping live auth objects?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how does config cloning decide which fields to preserve, redact, or restore?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_RUNTIME_FIELDS` (:96-101), `_SENSITIVE_FIELDS_EXACT` (:104-123), `_SENSITIVE_SUFFIXES` (:126-132), `_is_sensitive_field` (:254-267), `_safe_deepcopy_config` (:270-298).
**Signature:** `_is_sensitive_field(field_name) -> bool`; `_safe_deepcopy_config(config) -> config-or-dict-clone`.
**Data Shape:** three field classes: runtime allowlist `{http_auth, auth, connection_class, ssl_context}` (non-serializable LIVE OBJECTS); exact deny list (api_key, secret_key, private_key, *_token, credentials, …); suffix deny list (`_password`, `_secret`, `_token`, `_credential(s)`).

### Decisive source
```python
def _is_sensitive_field(field_name):
    name = field_name.lower().strip()
    if name in _RUNTIME_FIELDS:      # 1. allowlist wins FIRST
        return False
    if name in _SENSITIVE_FIELDS_EXACT:   # 2. exact deny
        return True
    return any(name.endswith(s) for s in _SENSITIVE_SUFFIXES)  # 3. suffix deny
...
# Restore runtime fields, redact sensitive ones
for field_name in list(clone_dict.keys()):
    if field_name in _RUNTIME_FIELDS and hasattr(config, field_name):
        clone_dict[field_name] = getattr(config, field_name)
    elif _is_sensitive_field(field_name):
        clone_dict[field_name] = None
```

**Flow:** try plain `deepcopy` → on failure (thread locks, clients): dump via pydantic `model_dump()` or `__dict__` → reattach the original runtime objects by reference → null out every sensitive match → reconstruct with the ORIGINAL class; last-resort anonymous object if construction fails.
**Invariant:** the allowlist is checked BEFORE the deny lists because `http_auth` contains the word "auth" and would otherwise be classified sensitive — yet it's a live boto/requests object the clone needs to stay functional; reconstruction failure degrades to a shallow dict clone rather than raising; used for the telemetry vector-store clone AND lazy entity-store configs (Qdrant embedded client sharing).
**Probe:** `tests/memory/test_safe_deepcopy_config.py` (dedicated suite: non-deepcopyable configs cloned; secrets nulled; runtime fields preserved).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_safe_deepcopy_config _is_sensitive_field _RUNTIME_FIELDS redact", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layered classifier verbatim — allowlist-before-deny order IS the mechanism; adapt the field vocabularies to your stack; omit nothing else.
