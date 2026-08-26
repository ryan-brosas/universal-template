<!-- capsule-v2 -->
# Lazy telemetry module gate — how do you keep an optional, network-capable dependency out of your package's import path?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how does a library expose `from browser_use.telemetry import ProductTelemetry` while guaranteeing that importing the package never imports posthog, its service module, or any heavy transitive dep until first use?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/telemetry/__init__.py` whole (48L) — `_LAZY_IMPORTS` dict (:17-22), `__getattr__` (:25-40), `TYPE_CHECKING` stubs (:8-14), `__all__` (:43-48). Consumer entry: `ProductTelemetry` singleton resolved on first `telemetry.capture` call from `Agent._log_agent_event`.
**Signature:** `def __getattr__(name: str)` at MODULE level (PEP 562); `_LAZY_IMPORTS: dict[str, tuple[str, str]]` mapping public name → (module_path, attr_name).
**Data Shape:** no eager imports beyond `typing.TYPE_CHECKING`; four public names (`ProductTelemetry`, `BaseTelemetryEvent`, `MCPClientTelemetryEvent`, `MCPServerTelemetryEvent`) declared in both the lazy map and `__all__`.

### Decisive source
```python
_LAZY_IMPORTS = {
	'ProductTelemetry': ('browser_use.telemetry.service', 'ProductTelemetry'),
	'BaseTelemetryEvent': ('browser_use.telemetry.views', 'BaseTelemetryEvent'),
	...
}

def __getattr__(name: str):
	if name in _LAZY_IMPORTS:
		module_path, attr_name = _LAZY_IMPORTS[name]
		try:
			module = import_module(module_path)
			attr = getattr(module, attr_name)
			globals()[name] = attr   # CACHE into module globals:
			return attr              # later accesses bypass __getattr__ entirely
		except ImportError as e:
			raise ImportError(f'Failed to import {name} from {module_path}: {e}') from e
	raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
```
**Flow:** `import browser_use.telemetry` executes only the dict + function defs → first attribute access triggers `__getattr__` → target module imported once → attribute cached in `globals()` so subsequent reads are plain dict lookups → unknown names still get the idiomatic AttributeError.
**Invariant:** the lazy map and `__all__` must stay in sync or IDE/type users drift from runtime behavior; caching MUST write into `globals()` (re-running `__getattr__` per access would still work but repeats import-module lookups); failures re-raise as ImportError WITH the original chained (`from e`) so missing optional deps diagnose clearly; anything NOT in the map must fall through to AttributeError — never silently return None.

**Probe:** executed live (repo .venv, cwd=repo root): before access `'ProductTelemetry' in vars(T)` → False; after `from browser_use.telemetry import ProductTelemetry` → cached-in-globals True; `T.DefinitelyNotThere` → AttributeError; `AgentTelemetryEvent.properties` injects `is_docker` and excludes `name`; judge fields default None. No dedicated unit test for `__init__.py` itself (documented caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "__getattr__ lazy import telemetry components _LAZY_IMPORTS", limit: 6, fields: ["lines"] });
```

## Verdict
Adopt PEP 562 module `__getattr__` + globals-caching for ANY optional-dependency surface (telemetry SDKs, vendor clients) so core import time stays flat and the dep only loads when a feature is actually used. Keep TYPE_CHECKING stubs so type checkers see the real types. Adapt the name list to your surface. Omit nothing — the pattern is 24 lines.
