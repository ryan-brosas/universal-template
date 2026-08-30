<!-- capsule-v2 -->
# Bind-tools exception taxonomy — how do three failure classes (capability gap, loud cap failure, unknown error) take three different paths through one resolver?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When native `bind_tools` can't happen, when must the run degrade to the unbound code-act model versus crash loudly — and how do you make that distinction machine-readable?

## resolve_model_with_bind_tools + _safe_bind + BindToolsUnsupportedError
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/helpers/bind_tools.py:25-61,412-422` (`_record_bind_tools_degraded`, `_safe_bind`, except-ladder); `src/cuga/backend/cuga_graph/nodes/cuga_lite/bind_tools/cap.py:35-43` (`BindToolsUnsupportedError`).
**Signature:** `async resolve_model_with_bind_tools(active_model, *, configurable, tools_context_ref, tool_provider, model_name=None, query=None, run_config=None) -> BaseChatModel`; `def _safe_bind(model, tools) -> Runnable`.
**Data Shape:** modes `none|find_tools|all|apps|tools|apps_and_tools` from configurable → per-model runtime profile → settings; returns a model (bound or not) or RAISES.

### Decisive source
```python
# helpers/bind_tools.py:42-51
def _safe_bind(model, tools):
    # ``BaseChatModel.bind_tools`` raises ``NotImplementedError`` by default, and
    # ``NotImplementedError`` is a subclass of ``RuntimeError`` — so without this
    # guard it would be caught by the cap's deliberate ``except RuntimeError:
    # raise`` in ``resolve_model_with_bind_tools`` and crash ``call_model``.
    try:
        return model.bind_tools(tools)
    except NotImplementedError:
        _record_bind_tools_degraded(f"{name} does not support bind_tools (bind step)")
        return model

# cap.py:35-43 — capability gap is deliberately NOT a RuntimeError
class BindToolsUnsupportedError(Exception):
    """...the cap/shortlist errors in this module are intentional loud failures
    re-raised by ``resolve_model_with_bind_tools``'s ``except RuntimeError: raise``.
    A missing provider capability is a different class of problem — the run can
    still proceed on the unbound (code-act) path."""

# helpers/bind_tools.py:412-421 — the ladder
except BindToolsUnsupportedError as e:
    logger.warning("{}", e); _record_bind_tools_degraded(str(e))   # degrade
except RuntimeError:
    raise                                                          # stay loud
except Exception as e:
    logger.warning("resolve_model_with_bind_tools failed: {}", e)  # degrade
```

**Flow:** mode resolution → per-mode candidate collection (overlay merge for skills/shell/find_tools; first-occurrence-wins on duplicate names) → cap+merge → `_safe_bind`. Failure paths: unsupported bind at ANY layer (including the shortlister running on the same model inside cap.py :183-192) ⇒ `BindToolsUnsupportedError` ⇒ log + tracker step `bind_tools_degraded` + return UNBOUND model; genuine shortlist failure / empty ranking / hallucinated-all-names ⇒ `RuntimeError` with actionable message ⇒ RE-RAISED so benchmark runs comparing native vs text mode never silently degrade; anything else ⇒ warn + unbound model.
**Invariant:** "Silent truncation is **not** an option" (:218-221) — a data-shrink failure is loud, a capability absence is quiet-but-recorded; the degraded trace exists because "nothing downstream can branch on a log line" (:26-33) and eval harnesses relabel/exclude such runs; `NotImplementedError ⊂ RuntimeError` ordering makes `_safe_bind`'s inner guard load-bearing.
**Probe:** no direct unit test for this module (coverage caveat — deterministic check: fake model whose `bind_tools` raises NotImplementedError must come back UNBOUND, never raise; fake shortlister returning garbage names must raise RuntimeError out of the resolver).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_model_with_bind_tools BindToolsUnsupportedError _safe_bind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-class taxonomy verbatim whenever an optional capability wraps a loud measurement path: degrade-with-machine-trace for capability gaps, re-raise for contract violations that would corrupt comparisons, generic-degrade otherwise; adapt mode names/settings plumbing; omit the overlay machinery if you have no in-graph tools outside your registry. Coverage caveat: source-read verified against both files; no dedicated test file.
