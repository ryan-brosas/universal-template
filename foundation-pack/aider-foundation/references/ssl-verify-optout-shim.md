<!-- capsule-v2 -->
# SSL-verify opt-out shim — live monkeypatch of litellm's lazy httpx sessions

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you honor a `--no-verify-ssl` flag when your HTTP stack constructs its clients lazily inside a third-party SDK?

## Force-load litellm, then swap BOTH sync and async module-level httpx sessions; mirror the flag on aider's model_info_manager
**Path/Symbol:** `aider/main.py` :519-527: `os.environ["SSL_VERIFY"] = ""`, `litellm._load_litellm()`, `litellm._lazy_module.client_session = httpx.Client(verify=False)`, `litellm._lazy_module.aclient_session = httpx.AsyncClient(verify=False)`, `models.model_info_manager.set_verify_ssl(False)`; `--openrouter-api-base` sibling handling nearby.
**Signature:** the patch is only safe AFTER `_load_litellm()` materializes `_lazy_module` — before that, attribute assignment would target a stub and be discarded.
**Data Shape:** env var `SSL_VERIFY=""` is read independently by litellm internals; the explicit session replacement covers code paths that ignore the env var.

### Decisive source
```python
if not args.verify_ssl:
    import httpx
    os.environ["SSL_VERIFY"] = ""
    litellm._load_litellm()
    litellm._lazy_module.client_session = httpx.Client(verify=False)
    litellm._lazy_module.aclient_session = httpx.AsyncClient(verify=False)
    # Set verify_ssl on the model_info_manager
    models.model_info_manager.set_verify_ssl(False)
```

**Flow:** parse → if verify-ssl disabled, eagerly pay the deferred-import cost to reach litellm's real module object, replace both session factories with verify=False twins, and propagate the setting to every OTHER component that issues LLM-side HTTP (model-info fetcher).
**Invariant:** this is a deliberate escape hatch that weakens TLS for ALL provider traffic — it exists for corporate MITM proxies; the invariant is COMPLETENESS (every HTTP-issuing surface covered), because one missed client silently re-enables verification and fails confusingly behind interception proxies.
**Probe:** deterministic anchors: `grep -nF 'SSL_VERIFY' aider/main.py` → :522; `grep -cF '_lazy_module' aider/main.py` → 2 (:524/:525). Direct tests: none upstream for this branch (source-pinned caveat; test_ssl_verification.py covers certifi bundle selection instead).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "set_verify_ssl model_info_manager", limit: 3 });
// resolves the main.py block + models.model_info_manager surface
```

## Verdict
Adopt the force-load-then-swap pattern when a lazy SDK hides session objects you must reconfigure; adapt scope. Document it as a security-relevant flag — porters who copy only the env-var half ship a no-verify flag that works intermittently depending on which litellm path fires first.
