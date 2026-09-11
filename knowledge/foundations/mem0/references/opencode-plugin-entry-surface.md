<!-- capsule-v2 -->
# OpenCode plugin entry surface — how does one async plugin function register a full memory toolset, context injection, and lifecycle finalization into a host that has no hook exit codes?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when the host's plugin model is "return an object of named hooks + a tool registry" (no shell hooks, no exit codes, no additionalContext channel), what is the complete registration surface a memory plugin must expose — and how do deny, inject, and cleanup map onto it?

## opencode-mem0.ts — no-key guard, 7-hook map, 10-tool registry, marker-guarded injection
**Path/Symbol:** `integrations/mem0-plugin/.opencode-plugin/opencode-mem0.ts` — `Mem0Plugin` (259–999): no-key guard (263–277), identity trio `getUserId`/`getProjectId`/`getBranch` (30–68), `generateSessionId` (75–78), `SECRET_PATTERNS`+`redact` (81–96), `autoSetupCategories` (139–173), detector regexes `NUDGE_RE`/`RESUME_RE`/`ERROR_STRONG_RE`/`WRITE_TOOLS` (175–184), `resolveFilters` (186–243), returned hook object (377–628: `shell.env` ~385–395, `config` ~397–415, `tool` registry 417–628 with 10 tools), `chatMessageHook` (630–855), `toolExecuteBeforeHook` (857–870), `chatMessagesTransformHook` (872–886), `toolExecuteAfterHook` (888–952), `compactionHook` (954–997); key resolution in `api-key.ts` — `parseApiKeyLine` (7–13), `resolveApiKey` (15–30).
**Signature:** `const Mem0Plugin: Plugin = async (ctx: { $, client }) => ({ "chat.message", "experimental.chat.messages.transform", "tool.execute.before", "tool.execute.after", "experimental.session.compacting", "shell.env", config, tool: {…10 tools} })`.
**Data Shape:** the seven returned hook keys match package.json `opencode.hooks` EXACTLY (`config, chat.message, tool.execute.before, tool.execute.after, experimental.chat.messages.transform, experimental.session.compacting, shell.env`) — the manifest is the contract; the `tool` registry (add_memory, search_memories, get_memories, get_memory, update_memory, delete_memory, delete_all_memories, delete_entities, list_entities, get_event_status) is separate from the hook list.

### Decisive source
```ts
const apiKey = resolveApiKey();
if (!apiKey) {
  try {
    await client.app.log({ body: { service: "mem0", level: "error",
      message: "MEM0_API_KEY environment variable not set. Get one at https://app.mem0.ai/dashboard/api-keys" }});
  } catch {}
  return {};                                   // plugin silently absent — host keeps working
}
```
Deny maps to THROW (the host surfaces tool errors to the agent): `tool.execute.before` throws `Error("Use the add_memory tool instead of writing to MEMORY.md")` when a Write/Edit/MultiEdit targets `/MEMORY\.md|\.claude\/memory/i`. Inject maps to MESSAGE TRANSFORM: accumulated `systemContext` lines are pushed ONCE as a `"## Mem0 Memory Context"` block unshifted into the first user message's parts, guarded by a marker scan so re-transforms are no-ops. Cleanup maps to `process.on("beforeExit", emitSessionStop)` — once-guarded session_stop telemetry + dream finalization (recordDreamCompletion iff dreamWriteSeen, releaseDreamLock always).

**Flow:** entry resolves key via api-key.ts ladder (env `MEM0_API_KEY` trimmed > five-profile scan `.zshrc/.bashrc/.zprofile/.bash_profile/.profile`, each line comment-stripped, quote-stripped, `$var`/`$(…)`-rejected — the TS port of the Python identity ladder's profile rung) → no key: one error log + `{}` → key: build MemoryClient, identity trio, `ses_<unix-ts>_<hex6>` session id, stats counters → background `autoSetupCategories` (same fingerprint latch as plugin-category-bootstrap-latch.md) → per-message pipeline: <10-char gate → 6-pattern secret redaction → once-init (session-count increment, getAll pageSize=1 three-shape count unwrap, guidance + SCOPE_GUIDANCE push, prefetch topK=5, session_start event, dream gates) → NUDGE_RE ⇒ "[MEMORY TRIGGER] … confidence=1.0, infer=false" context → RESUME_RE ⇒ two parallel topK=3 searches deduped by memory id → else raw-text prefetch topK=5 → msgCount%3==0 background auto_capture add (confidence 0.7) → msgCount%5==0 && adds < msgCount/3 store-nudge → user_prompt event. `shell.env` exports MEM0_USER_ID/APP_ID/SESSION_ID/BRANCH/GLOBAL_SEARCH into spawned shells; `config` appends the bundled opencode-skills dir to `skills.paths` AND registers a `/mem0-<skill>` slash command per skill (skills.paths alone does NOT create slash commands — the TUI menu reads `config.command`).
**Invariant:** the no-key guard returns `{}` AFTER logging — a plugin that throws at entry would break the host; silent absence is the failure posture (contrast the Python suite's fail-open envelope, same philosophy different mechanism). The transform marker guard is what makes injection idempotent across host re-transforms. The bash-error detector exempts `git commit|merge|rebase` output and requires either a strong error signature or ≥2× `Error:/Exception:` before spending a search. Every network call in the pipeline is individually try/catch-swallowed — one dead endpoint degrades to silence, never to a broken turn.
**Probe:** `.opencode-plugin/api-key.test.ts` (8 tests under bun: 7 green / 1 environmental) — pins parseApiKeyLine accept/reject matrix (export form, quotes+comment, `$VAR` and `$(cat …)` rejection, empty rejection), resolveApiKey env-wins / first-valid-profile / unreadable-profile-skip / unsupported-file-ignore, and the two ENTRY tests: missing-key ⇒ exactly one error log + `plugin === {}`; profile-recovered key ⇒ zero logs + returned object contains `chat.message` and `tool`. The profile-recovery test FAILS in this environment solely because bun 1.4.0 caches `os.homedir()` from startup $HOME (probed directly: runtime `process.env.HOME` changes are ignored; pre-set HOME is honored) — Node semantics would pass it; recorded as environment caveat, not source defect.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "Mem0Plugin", limit: 10, fields: ["signature", "name", "file"] });
```
(MCP not connected this session — direct whole-file read of all 1,000L + api-key.ts + api-key.test.ts executed instead; record in verification.md pass 10.)

## Verdict
Adopt the surface mapping itself: deny=throw-with-coaching-message, inject=marker-guarded first-user-message transform, cleanup=once-guarded beforeExit, absence=log-then-empty-object, identity-export=shell.env, discoverability=config.command slash commands alongside skills.paths. Adapt the detector regexes and cadence moduli to your host's tool names; keep the per-call swallow discipline. Omit the mem0ai SDK specifics and the PostHog wiring (see opencode-telemetry-parity.md). This capsule is the TS twin of plugin-hook-failopen-envelope.md + plugin-prompt-context-compiler.md combined — the Python suite splits those concerns across shell hooks; here one object owns them. Coverage: fully indexed plane, whole file read; direct tests run under bun 1.4.0 with the one environmental caveat above.
