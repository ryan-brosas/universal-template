<!-- capsule-v2 -->
# MCP server as a native-or-local capability — URL-derived stable ids, spec-serializable subset, and the callable-native id trap

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/mcp.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you wrap "connect to an MCP server" as one capability that serves BOTH a native MCP advertisement (for models that support it) and a locally-connected toolset (for those that don't), with ids stable enough that the local side's `unless_native` marker always matches what's actually advertised? A porter will derive ids inconsistently between the two sides and break the pairing.

## Path / Symbol
`capabilities/mcp.py` — `MCP(NativeOrLocalTool)` dataclass(init=False) (:26–213): url-required-for-native guard (:76–83), fastmcp-object wrapping of unrecognized `local=` inputs (:88–104), `_derive_id(url)` precedence (:112–132), `_resolved_id` cached_property with callable-native UserError (:134–147), `_default_native` (:149–159), `_native_unique_id → f'mcp_server:{id}'` (:161–162), `_default_local` (:164–168), `_require_url` strategy validation (:170–184, :251–258), `_build_local` header merge + ImportError→UserError (:186–206), allowed_tools post-filter (:208–213), spec-restricted `from_spec` (:215–248).

## Signature
```python
def _derive_id(self, url: str | None) -> str | None:
    # explicit id → native MCPServerTool.id → f'{host}-{path_slug}' (or bare host/url); None only
    # when there is nothing at all to derive from
```

## Data Shape
Constructor accepts runtime-wide `local=` (URL string, `fastmcp.Client`, transport, in-process FastMCP server, script path, pre-built toolset) but `from_spec` restricts to the JSON/YAML-serializable subset (`str | bool | None`) so AgentSpec schema generation works. Non-string non-toolset non-callable locals are wrapped `MCPToolset(local, include_instructions=True, id=self._derive_id(self.url))`. Local connection headers = `headers ∪ {Authorization: authorization_token}`.

### Decisive source
The id-stability contract (:119–147):
```python
if isinstance(self.native, MCPServerTool):
    return self.native.id   # key off it so the local fallback's `unless_native`
                            # marker matches the native tool actually advertised
...
resolved = self._derive_id(self.url)
if resolved is None:
    raise UserError('MCP(native=<callable>) paired with a local fallback needs a stable `id` '
                    'to tie the two together (the local fallback is tagged with the native id '
                    'via `unless_native`). Pass `url=`, `id=`, or use an explicit native=MCPServerTool(...)')
```

**Flow:** `native=True` requires `url=` up-front (the capability auto-builds the MCPServerTool; explicit instances/callables carry their own). Local build infers SSE vs Streamable-HTTP from the URL; missing `mcp` extra converts ImportError into a UserError that also advertises the escape hatch `MCP(url=…, native=True, local=False)` (works without the extra). `local=True` derives from `url=`; a string `local=` must be an http(s) URL (`_require_url`) so the same value roundtrips through specs and can be re-served as native. Hostname is INCLUDED in the derived slug to avoid collisions across hosts (two `/sse` URLs).

**Invariant:** The local fallback's exclusion tag and the native advertisement MUST derive from the same id chain; when nothing can anchor it (callable native, no url, no id) the run must fail loudly rather than pair against a phantom id. `allowed_tools` filters the LOCAL toolset post-construction via `toolset.filtered(name-in-set)`; native-side filtering happens inside MCPServerTool.

**Probe:** `tests/test_capabilities.py` — deferred-capability/native partition tests around `test_deferred_capability_partitions_native_tools` (:3235); MCP spec construction `test_agent_from_spec_mcp` (:241). Coverage caveat: no dedicated unit file for `_derive_id` precedence — behavior pinned indirectly through spec/e2e runs.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'MCP capability MCPServerTool MCPToolset unless_native'
```

## Verdict
**Adopt** the single-id-chain derivation (explicit → native-instance → host+slug), the loud failure when a callable-native has no anchor, the serializable-subspec pattern, and the ImportError→instructive-UserError conversion. **Adapt** the toolset class names; keep `include_instructions=True` semantics for local MCP connections. **Omit** the native plane entirely for hosts without native-MCP providers — the local-only path still needs the id stamping for durable execution.
