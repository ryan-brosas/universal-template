<!-- capsule-v2 -->
# Headless runner contract — how does a supervisor drive a one-shot headless CLI agent so its result normalizes into the ordinary run record without ARG_MAX or session-state leaks?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what argv/envelope contract lets a parent process treat a stateless one-prompt CLI (Veda) exactly like an interactive agent child?

## One invocation = one prompt: argv builder + stdin task + envelope normalization
**Path/Symbol:** `src/agents/veda-cli.ts` whole (:1-73 — `VEDA_TOOL_NAMES`, `mapVedaTools`, `normalizeVedaModel`, `vedaReasoning`, `buildVedaArguments`); spawn-side consumption `src/worker.ts:320-329`; runner validation `src/agents/manager.ts:469-495`.
**Signature:** `buildVedaArguments(options: VedaRunArguments): string[]`; `mapVedaTools(tools: readonly string[]): string[]`; `normalizeVedaModel(model: string): string`; `vedaReasoning(thinking: FabricThinking): string`.
**Data Shape:** argv `-b <backend> -p <persona> [-m <model>] [-r <reasoning>] (--tools <csv> | --no-tools) --json --no-sel -S fabric-<runId> --no-notify`; task delivered over **stdin**; stdout JSON envelope `{text, sessionId?, usage?: {inputTokens, outputTokens, cachedTokens, costUsd}, error?, design?, worker?}` normalized into the ordinary run record (`record.text`, `record.runnerSessionId`, `record.usage` with `cacheWrite` forced to 0).

### Decisive source
```ts
// src/agents/veda-cli.ts:64-73 — the whole argv contract
export const buildVedaArguments = (options: VedaRunArguments): string[] => {
  const tools = mapVedaTools(options.tools);
  const args = ["-b", options.backend, "-p", options.persona];
  if (options.model) args.push("-m", normalizeVedaModel(options.model));
  if (options.thinking) args.push("-r", vedaReasoning(options.thinking));
  if (tools.length > 0) args.push("--tools", tools.join(","));
  else args.push("--no-tools");
  args.push("--json", "--no-sel", "-S", options.session, "--no-notify");
  return args;
};
// src/worker.ts:326-328 — why the session name exists
// Isolate selection and conversation state per child run so
// parallel Fabric agents never share Veda session state.
session: `fabric-${options.id}`,
```

**Flow:** spawn validates `runner ∈ {pi, claude, veda}` (:474-476) → persona option is veda-only (:477-479) → portable tool names map through `VEDA_TOOL_NAMES` (`find`/`ls` both collapse to `glob`; an unmapped tool **throws** naming the supported set, :30-44) → model is stripped of a `veda/` routing prefix and otherwise forwarded literally (:48-55) → `thinking:"off"` degrades to `"minimal"` because Veda has no off level (:57-59) → argv assembled, prompt piped to stdin → worker parses the final stdout envelope; `text` echoes to stdout and lands in `record.text`, `sessionId` becomes `runnerSessionId`, usage tokens normalize with `costUsd` defaulting to 0.
**Invariant:** backends and models are pass-through strings — the former `VEDA_BACKENDS` allowlist was deliberately REMOVED (upstream 06a13dd) so backends registered by a custom Veda build keep working; only tool names are gated (the CLI maps them per-backend). Per-run `-S fabric-<runId>` isolation is what makes parallel children safe; dropping it shares selection/conversation state across children. Long prompts must ride stdin, never argv (ARG_MAX).
**Probe:** `tests/worker-e2e.test.ts:160` (behavior `"success"`: status `completed`, `text` contains `"echo:"`, `usage` matches `{input: 10, output: 5, cacheRead: 2, cacheWrite: 0}`, `runnerSessionId === "conv-1"`, `turns === 1`) against the stub binary `tests/fixtures/fake-veda.mjs`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "buildVedaArguments mapVedaTools normalizeVedaModel vedaReasoning", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-invocation-one-prompt shape: stdin task, minimal argv, JSON-envelope normalization into the host's ordinary result record, per-run session naming. Adapt backend/persona vocabulary and tool-name tables to your CLI; omit Veda persona semantics unless driving the same binary. Direct coverage is the real-worker e2e suite (`describe.skipIf(!hasWorker)` — needs a runnable worker build; deterministic probes above stand in elsewhere).
