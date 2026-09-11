<!-- capsule-v2 -->
# Hook fail-open envelope — how does a memory side-channel attach to a host agent loop without ever blocking or failing it?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** what failure posture must a hook/plugin keep so the worst case is silence, never a blocked prompt or broken tool call?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/on_pre_compact.py` `__main__` wrapper (:309-314) and `store_memory` bool returns (:193-202); `auto_capture.py` wrapper (:208-213); `_search.py:search_memories` catch-all (:87-89); `hooks.json` every command ends `|| true`.
**Signature:** `def main() -> None`; wrapper: `try: main()\nexcept Exception as e: log.error(...); sys.exit(0)`.
**Data Shape:** stdin JSON or argv in; stderr-only logs out; network helpers return `bool`/`list`, never raise across module boundary.

### Decisive source
```python
# on_pre_compact.py — every entrypoint ends like this
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("Unexpected error: %s", e)
    sys.exit(0)

# _search.py — even total failure is an empty result, logged once to stderr
    except Exception as e:
        print(f"[mem0] search request failed: {e}", file=sys.stderr)
        return []
```

**Flow:** host fires hook → script resolves inputs defensively (missing key/file/JSON → early return) → optional work → any exception lands in the wrapper → exit code is ALWAYS 0.
**Invariant:** no raise may cross the script boundary; stdout carries only deliberate context payloads; happy path writes nothing to stderr; logging goes through the `:80-`-style `[mem0-*]` stderr handler (MEM0_DEBUG additionally mirrors to ~/.mem0/hooks.log).
**Probe:** `cd $REFERENCE_ROOT/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_search.py -q` (pins 429→[]+stderr AND happy-path-silent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "mem0", qualified_name: "mem0.integrations.mem0-plugin.scripts.on_pre_compact.store_memory" });
```

## Verdict
Adopt the always-exit-0 wrapper + typed-return helpers + stderr-only discipline for ANY in-host side-channel (telemetry, memory, cache warmers); adapt log prefixes/flag file paths to the host; omit the mem0 REST specifics. Caveat: shell-hook tests execute bash via subprocess — same suite also pins the rubric cadence.
