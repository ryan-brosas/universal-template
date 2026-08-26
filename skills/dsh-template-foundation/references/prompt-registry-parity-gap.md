<!-- capsule-v2 -->
# Phantom-command registration — what happens when the command registry and the prompt dir disagree?

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** If a slash-command is registered for a prompt file that does not exist on disk, where exactly does it fail — and should a template validate registry↔disk parity?

## Registry↔disk parity gap in DEFAULT_COMMANDS
**Path/Symbol:** `.dsh/plugins/project-prompts/src/index.js` — `DEFAULT_COMMANDS` (:33–43) lists `verify: ["verify.md", …]` at :39; `.dsh/prompts/` contains only 8 files (init, create, plan, ship, fix, research, audit, gc + README).
**Signature:** registration-time surface = all 9 `DEFAULT_COMMANDS` keys; invocation-time surface = whichever `.md` files actually exist under `config.promptDir`.
**Data Shape:** `/verify` registers successfully (registration never touches disk); at invocation the handler's FIRST statement is an existence check that returns `{ kind:"error", text:"prompt file not found: <abs path>" }`.

### Decisive source
```js
// DEFAULT_COMMANDS :33-43 — verify.md is declared but absent from .dsh/prompts/
verify:   ["verify.md",   "run gates against the spec"],
// handler :78 — the deferred failure point:
if (!existsSync(promptPath)) return { kind: "error", text: "prompt file not found: " + promptPath };
```

**Flow:** (1) plugin `apply` mounts all nine commands including `/verify`; (2) user invokes `/verify`; (3) handler checks `existsSync(promptPath)` → false; (4) returns a structured error result naming the missing path — no crash, no model round-trip. The defect is invisible until first use because nothing validates parity at boot.
**Invariant:** registration is optimistic, validation is lazy — the registry trusts `DEFAULT_COMMANDS` and the disk is consulted only per-invocation; the failure is graceful (typed error result), so the cost is UX (a dead command advertised in README table line 12) rather than stability. A porter should either ship every registered file or add a boot-time/CI parity check (e.g. in check.mjs section 3b style) instead of copying this asymmetry.
**Probe:** executed live at HEAD: census of `DEFAULT_COMMANDS` vs disk → `verify MISSING` (8 OK / 1 MISSING); replica of handler logic returned `{"kind":"error","text":"prompt file not found: /mnt/ssd/work/project/dsh-template/.dsh/prompts/verify.md"}`; documentation side confirmed (`grep -n '/verify' .dsh/prompts/README.md` → line 12). No test runner exists (coverage caveat: deterministic probes only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "DEFAULT_COMMANDS resolveCommands apply followup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lesson, not the bug: keep registry↔artifact parity mechanically checked when commands map to files (or make registration itself stat the files). Adapt the parity-check placement to your host's gate. Omit the lazy-existence design for any command whose absence is dangerous rather than merely dead.
