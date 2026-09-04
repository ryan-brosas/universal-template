<!-- capsule-v2 -->
# dsh-mem0 fail-soft tool errors — should a memory tool reject or degrade?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** When the Mem0 backend call throws mid-conversation, does the agent see a rejected tool call or a readable failure line?

## Catch-and-render error envelope
**Path/Symbol:** `integrations/dsh-mem0/src/index.ts` (`execute` catch arms :106-108 and :132-134).
**Signature:** `catch (err) { return \`<tool> failed: ${err instanceof Error ? err.message : String(err)}\`; }`.
**Data Shape:** ALWAYS resolves to a string — success renders via formatter+truncator; failure renders `<toolname> failed: <message>` (Error.message, or String() for thrown non-Errors).

### Decisive source
```ts
} catch (err) {
  return `search_memory failed: ${err instanceof Error ? err.message : String(err)}`;
}
```

**Flow:** execute try-body → on ANY rejection render `search_memory failed: …` / `add_memory failed: …` and RETURN it as normal tool output.
**Invariant:** Tool-level failures are FAIL-SOFT: they never propagate to the harness as rejections — the model reads the reason and can retry or continue. This is the deliberate OPPOSITE of the sibling family (`integrations/pi-agent-plugin/src/memory/tools.ts` buildToolExecute throws on abort/validation and its wrapper re-throws after telemetry), so a porter must choose per host: conversation-continuity favors dsh-mem0's swallow-and-report; audit/telemetry pipelines favor pi-agent-plugin's throw. Mount-time misconfiguration is NOT covered by this envelope — config errors throw inside `apply` before any tool exists.
**Probe:** `integrations/dsh-mem0/tests/apply.test.ts` ("returns a graceful failure line instead of rejecting on error" asserts output contains "search_memory failed"+"network down"; add twin "returns a graceful failure line on error" with "boom") — green offline.
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `truncateOutput formatMemoryList` limit 3 → BOTH pipeline functions resolve line-exact (`…src.output.truncateOutput` 12-33 rank 1, `…src.formatting.formatMemoryList` 34-39 rank 2).

## Verdict
Adopt the per-tool prefixed failure-string envelope (name in message, Error-vs-String discrimination) when your host tolerates soft tool failures; adapt by moving the catch to your framework's tool-wrapper layer if tools there share one executor. Omit global error handlers that would convert these back into rejections — the point is the model-readable line.
