<!-- capsule-v2 -->
# TS-SDK Wire Translation — how does a camelCase SDK speak to a snake_case server without silent field drops?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Where must camelCase→snake_case translation live so Pydantic's `extra="ignore"` can't silently discard caller config?

## Plain-interface wire boundary with two hand serializers
**Path/Symbol:** `packages/typescript-sdk/src/internal/wire.ts` — `serializeAssignTo` (:55–61), `serializeVerifierConfig` (:81–93), `CreateTaskRequestWire` (:17–30).
**Signature:** `serializeAssignTo(assignTo: unknown): unknown | null`; `serializeVerifierConfig(config: VerifierConfig | undefined | null): VerifierConfigWire | null`.
**Data Shape:** AssignTo: string → `{email}`, Array → `{emails}`, object passthrough, other → `{value: String(x)}`; VerifierConfig camelCase `{provider, model?, instructions, maxAttempts, apiKeyEnv?}` → snake_case `{provider, model?, instructions, max_attempts, api_key_env?}` (optional keys only set when defined).

### Decisive source
```ts
/**
 * Convert the caller-facing `VerifierConfig` (camelCase, idiomatic TS)
 * into the snake_case wire shape the Python server's Pydantic
 * `VerifierConfig` validates against. Without this translation the
 * server's `extra="ignore"` default silently drops camelCase fields
 * and the verifier runs with `max_attempts=3` regardless of the
 * caller's choice.
 */
```

**Flow:** caller options (idiomatic camelCase) → serialize at exactly one chokepoint per call site (`await-human.ts:129/:131`, langgraph adapter :203/:205) → flat snake_case JSON body POSTed to `/api/tasks`.
**Invariant:** translation happens in `internal/wire.ts` ONLY — no ad-hoc renames at call sites; response parsing is NOT mirrored here because "the server is the source of truth for validation; the SDK trusts responses it receives" (module header) — wire types are plain `interface`s, deliberately not Zod.
**Probe:** `packages/typescript-sdk/src/await-human.ts` imports are the direct consumers; upstream has no dedicated wire unit test (SDK tests cover idempotency/forms/discovery) — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "serializeAssignTo serializeVerifierConfig CreateTaskRequestWire", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-module translation boundary + the "requests translated, responses trusted" asymmetry. Adapt the exact key tables to your server's Pydantic schemas. Omit the `unknown | null` looseness only if you have end-to-end schema tests on both sides. Caveat: no direct upstream unit test pins these functions.
