<!-- capsule-v2 -->
# Plugin telemetry privacy envelope — how does a hook send usage analytics from five editor surfaces without ever leaking content, keys, or raw ids?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when a memory plugin runs inside arbitrary editors and must report anonymous usage, how do you build one fire-and-forget sender whose identity, platform attribution, and property precedence hold across every host?

## scripts/telemetry.py — hashed ids, env-ladder platform, system-props-win payload
**Path/Symbol:** `integrations/mem0-plugin/scripts/telemetry.py` — `_distinct_id` (63–69), `detect_platform` (72–88), `is_enabled` (91–92), `build_posthog_payload` (95–114), `send` (117–128), `emit` (131–134).
**Signature:** `build_posthog_payload(event_name: str, properties: dict | None = None) -> dict`; `emit(event_type, properties)`; CLI `python3 telemetry.py <event> [--flags]` invoked as a BACKGROUND subprocess by the hooks (`... telemetry.py user_prompt --error_detected &`).
**Data Shape:** PostHog capture body `{api_key, distinct_id, event: "plugin.<type>", properties:{...caller, source:"plugin", platform, plugin_version, project_hash, os, os_version, sample_rate, $process_person_profile:false, $lib:"posthog-python"}}`.

### Decisive source
```python
# Never sends: user content, memory content, API keys, raw user/project IDs.
# Only sends: event type, platform, plugin version, anonymized hashes, counts.
...
def _distinct_id() -> str:
    """Stable anonymous ID: SHA-256 of API key if available, else SHA-256 of username."""
    api_key = os.environ.get("MEM0_API_KEY") or os.environ.get("CLAUDE_PLUGIN_OPTION_MEM0_API_KEY") or ""
    if api_key:
        return hashlib.sha256(api_key.encode()).hexdigest()[:32]
    user_id = os.environ.get("MEM0_RESOLVED_USER_ID") or os.environ.get("USER") or "unknown"
    return _sha256(user_id)
```
Payload spread order is the precedence contract: `properties: {**(properties or {}), "source": "plugin", "platform": plat, ...}` — SYSTEM properties are listed AFTER caller props so they always win.

**Flow:** hook backgrounds the CLI → `is_enabled()` (opt-out `MEM0_TELEMETRY ∈ {false,0,no,off}`) → build payload: distinct_id = sha256(api_key)[:32] else sha256(user); platform via explicit `MEM0_PLATFORM` then env-sentinel ladder (ANTIGRAVITY_PLUGIN_ROOT > KIMI > PLUGIN_ROOT=codex > CLAUDECODE/CLAUDE_PLUGIN_ROOT > CURSOR > WINDSURF > "plugin"); plugin_version read from THAT platform's own manifest (antigravity rides 0.1.x while claude/cursor/codex ride 0.2.x) with "unknown" fallback → POST to PostHog with 2s timeout wrapped in bare `except Exception: pass`.
**Invariant:** identity is stable but never reversible in-band: hashes only, never the key/user/project strings (test asserts raw values absent from the serialized payload); `$process_person_profile=False` prevents server-side person creation; telemetry failure can never surface (bare-except swallow) and opt-out short-circuits BEFORE any payload build. Platform attribution is pinned per surface because hosts don't export their sentinels uniformly: cursor wrappers must `export MEM0_PLATFORM=cursor`, codex standalone hook commands embed `MEM0_PLATFORM=codex` inline.
**Probe:** `integrations/mem0-plugin/tests/test_telemetry.py` (19 tests) — pins opt-out variants, payload structure + no-raw-string leak, `test_system_props_override_caller_props` (H8: source/platform/plugin_version beat caller-supplied values while caller-only props survive), distinct_id derivation both rungs, per-platform detection including antigravity-sets-both-vars, per-editor manifest version pinning, silent URLError swallow, and the cursor-wrapper/codex-hooks platform-pin greps.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mem0", query: "telemetry", limit: 12 });
```
Executed live with `file_pattern: "scripts/telemetry.py"`: returns all nine functions with line ranges matching this capsule.

## Verdict
Adopt the hashed-identity + hash-only-project contract, system-properties-win spread order, and the background-subprocess invocation so hooks never pay telemetry latency. Adapt the platform ladder's sentinel names and per-surface manifest lookup to your host set; keep an explicit override var first. Omit PostHog specifics if your sink differs — the shape survives any sink. Distinct from core `telemetry-sampling-singleton.md` (SDK-side before_send sampling): THIS is the plugin-side sender sharing the same `plugin.*` namespace; `.opencode-plugin/telemetry.ts` mirrors this exact schema for the TS surface. Coverage: fully indexed, whole 176L file read.
