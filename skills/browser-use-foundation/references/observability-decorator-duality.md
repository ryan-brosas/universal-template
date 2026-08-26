<!-- capsule-v2 -->
# Observability decorator duality — how do you ship tracing decorators that are real spans in production, debug-only spans, or no-ops, without call sites caring?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you wrap hundreds of functions with observability decorators when the tracer is an optional dependency AND one tier should activate only under debugging, while preserving signatures and async/sync behavior?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/observability.py` whole (204L) — availability probe (:43-55), `_create_no_op_decorator` (:58-84), `observe` (:87-131), `observe_debug` (:134-183), `_is_debug_mode` (:31-39), `get_observability_status` (:197-204). Consumers: `screenshot-disk-ledger` seam wraps ScreenshotService methods; `python_highlights.create_highlighted_screenshot`.
**Signature:** `observe(name=None, ignore_input=False, ignore_output=False, metadata=None, span_type='DEFAULT', **kwargs) -> Callable[[F], F]`; same shape for `observe_debug`; `_create_no_op_decorator(**kwargs)` returns the identity decorator.
**Data Shape:** module-level flags `_LMNR_AVAILABLE: bool`, `_lmnr_observe` resolved ONCE at import; status dict of four booleans.

### Decisive source
```python
_LMNR_AVAILABLE = False
try:
	from lmnr import observe as _lmnr_observe
	_LMNR_AVAILABLE = True
except (ImportError, TypeError):   # TypeError catches BROKEN installs, not just absence
	_LMNR_AVAILABLE = False

def _create_no_op_decorator(...):
	def decorator(func):
		if asyncio.iscoroutinefunction(func):
			@wraps(func)                       # signature/name/docstring preserved
			async def async_wrapper(*args, **kwargs):
				return await func(*args, **kwargs)
			return async_wrapper
		else:
			@wraps(func)
			def sync_wrapper(*args, **kwargs): return func(*args, **kwargs)
			return sync_wrapper
	return decorator

def observe_debug(...):
	kwargs = {..., 'tags': ['observe_debug']}  # tags must exist in Laminar FIRST
	if _LMNR_AVAILABLE and _lmnr_observe and _is_debug_mode():
		return _lmnr_observe(**kwargs)         # real spans only: installed AND LMNR_LOGGING_LEVEL=debug
	return _create_no_op_decorator(**kwargs)

def _is_debug_mode() -> bool:
	return os.getenv('LMNR_LOGGING_LEVEL', '').lower() == 'debug'
```
**Flow:** import time decides availability once → `observe()` returns the vendor decorator whenever lmnr exists (always-on tier) → `observe_debug()` additionally requires the env gate (debug tier) → everything else gets a transparent pass-through wrapper → call sites stay identical across all three regimes.
**Invariant:** the availability probe runs EXACTLY once at module import (per-process decision; no re-check per call); the no-op branch must preserve coroutine-ness and `__name__`/`__doc__` or await-sites and span-name derivation break; DRIFT WARNING pinned by direct read: the `observe_debug` docstring claims three debug signals (`DEBUG`, `BROWSER_USE_DEBUG`, root logging level) but the implementation checks ONLY `LMNR_LOGGING_LEVEL=debug` — trust the code. Vendor tag lists are hardcoded per tier because Laminar drops unknown tags.

**Probe:** executed live (repo .venv, lmnr absent): `get_observability_status()` → all four booleans False; `observe_debug(...)(async fn)` preserves `__name__` and passes through the awaited result (42); `observe(...)(sync fn)` passes values and name through. No dedicated unit test for observability.py itself (documented caveat); its ignore_input/ignore_output contract is consumed by the screenshot-disk-ledger seam.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "observe observe_debug _create_no_op_decorator _is_debug_mode get_observability_status lmnr", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt the two-tier duality + import-time probe + async/sync-preserving no-op as the standard optional-tracer shim for any Python library; adopt the TypeError-in-except detail for robustness against broken installs. Adapt the env gate name and vendor kwargs to your tracer. Omit the Laminar-specific tag pre-creation requirement if your backend auto-creates tags.
