<!-- capsule-v2 -->
# Scheduler model key — what identity makes two requests map to the same loaded runner?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** What is the correct cache key for the loaded-runner map when some models have no GGUF file path?

## schedulerModelKey fallback ladder
**Path/Symbol:** `server/sched.go:110-127` (`schedulerModelKey`). **Signature:** `func schedulerModelKey(m *Model) string`.
**Data Shape:** Input is a possibly-nil `*Model`. Returns ModelPath when non-empty; else `"digest:" + m.Digest` for safetensors/image models; else Name; empty string only if all three are absent.

### Decisive source
```go
func schedulerModelKey(m *Model) string {
    if m == nil { return "" }
    if m.ModelPath != "" { return m.ModelPath }
    if m.Digest != ""  { return "digest:" + m.Digest }
    if m.Name != ""    { return m.Name }
    ...
}
```

**Flow:** Every scheduler site (`getRunner` fast-path lookup, `processPending` pending-key check, `processCompleted` finished/expired bookkeeping, `load()` insertion, `expireRunner`, `evictAllAndWait` keep-key comparison) resolves identity through this ONE function, so GGUF models (keyed by blob path) and safetensors/MLX models (keyed by manifest digest with a literal prefix to never collide with a path) share one map safely.
**Invariant:** Never key by user-facing name alone: two tags can alias one manifest and a re-pull changes digests. The digest prefix exists because a path and a raw digest string must not be able to alias.
**Probe:** `grep -c "schedulerModelKey" server/sched.go` → `12` call sites (single definition); direct test coverage via `server/sched_test.go` suite (PASS at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "schedulerModelKey", limit: 5 });
```

## Verdict
Adopt the ordered fallback ladder (file path → prefixed content digest → name). Adapt the prefix spelling to your own storage layout; omit MLX-specific ShortName substitution in `load()` unless porting that runner too.
