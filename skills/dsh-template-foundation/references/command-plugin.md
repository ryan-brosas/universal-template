<!-- capsule-v2 -->
# Command plugin — turn `.dsh/prompts/*.md` into DSH slash-commands

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a DSH command-plugin register each `.dsh/prompts/<name>.md` as a slash-command that loads the file and feeds it back to the agent — without sending the invocation to the model?

## DSH command-plugin (`ctx.commands.register`)
**Path/Symbol:** `.dsh/plugins/project-prompts/src/index.js` (whole file, 93 lines); exports `name` (29), `inject` (30), `DEFAULT_COMMANDS` (33–43), `Config` (46–54), `resolveCommands` (56–64), `apply` (66–93).
**Signature:** `export const name = "project-prompts"`; `export const inject = ["commands"]`; `export function apply(ctx, config = {})`; `export const Config = Schema ? Schema.object({...}) : undefined`.
**Data Shape:** `DEFAULT_COMMANDS` maps command name → `[file, description]` (init/create/plan/ship/fix/verify/research/audit/gc). `Config` (when schemastery resolves) is `Schema.object({ promptDir: string, commands: Schema.dict({ file, description }) })`. `apply` resolves `dir = resolve(config.promptDir ?? join(process.cwd(), ".dsh", "prompts"))`, merges custom commands over defaults, and registers each via `ctx.commands.register({ name, description, input, handler })`.

### Decisive source
```js
import { createUserMessage } from "@deepseek-ai/dsh-llm";
let Schema;
try { ({ default: Schema } = await import("@deepseek-ai/schemastery")); } catch { Schema = undefined; }

export const name = "project-prompts";
export const inject = ["commands"];

// A config row can override the prompt dir or per-command files.
export const Config = Schema
  ? Schema.object({
      promptDir: Schema.string().default(join(process.cwd(), ".dsh", "prompts")),
      commands: Schema.dict(Schema.object({
        file: Schema.string().required(),
        description: Schema.string().default(""),
      })).default({}),
    })
  : undefined;

function resolveCommands(config) {
  const custom = config?.commands ?? {};
  const merged = { ...DEFAULT_COMMANDS };
  for (const [cmd, spec] of Object.entries(custom)) {
    const cur = merged[cmd];
    merged[cmd] = cur ? { file: spec.file ?? cur[0], description: spec.description ?? cur[1] }
                      : { file: spec.file, description: spec.description ?? "" };
  }
  return merged;
}

export function apply(ctx, config = {}) {
  const dir = resolve(config.promptDir ?? join(process.cwd(), ".dsh", "prompts"));
  const commands = resolveCommands(config);
  for (const [command, { file, description }] of Object.entries(commands)) {
    const promptPath = join(dir, file);
    ctx.commands.register({
      name: command,
      description,
      input: { hint: "[optional objective appended to the prompt]" },
      handler: (invocation) => {
        if (!existsSync(promptPath)) return { kind: "error", text: "prompt file not found: " + promptPath };
        const body = readFileSync(promptPath, "utf8");
        const extra = invocation.rawInput.trim();
        const text = extra ? body + "\n\nUser objective: " + extra : body;
        invocation.agent.followup(createUserMessage({
          content: [{ type: "text", text }],
          source: { kind: "user" },
        }));
        return { kind: "success", text: "/" + command + " started — prompt submitted to the agent." };
      },
    });
  }
}
```

**Flow:** (1) try-import schemastery for `Config` validation (falls back to `undefined` if unresolvable); (2) `apply` resolves the prompt dir and merges custom command overrides over `DEFAULT_COMMANDS`; (3) for each command, `ctx.commands.register` mounts a handler; (4) on invocation, the handler reads the prompt file, appends any raw input as `User objective:`, and submits it back to the agent via `invocation.agent.followup(createUserMessage({ content: [{type:"text",text}], source:{kind:"user"} }))` — never sending the invocation to the model; (5) returns `{ kind: "success"|"error", text }`.

**Invariant:** the handler is user-callable and does NOT round-trip through the model — it feeds the prompt body back as a user message; a missing prompt file returns a `{kind:"error"}` result, never a crash; custom commands override defaults field-by-field without dropping the rest.

**Probe:** no direct test file exists in the repo. Verified by direct source read (the file is indexed `no_recorded_issue` but its symbols are not surfaced as graph nodes). The wiring is documented in `.dsh/profile/cordis.patch.yml` (mount via a relative plugin path `name: './.dsh/plugins/project-prompts/src/index.js'`). Coverage caveat: plugin symbols are not graph-resolvable; source is the authority.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "project-prompts commands register followup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `ctx.commands.register` command-plugin contract (inject `commands`, optional `Config` schema, `apply` that registers handlers, `invocation.agent.followup(createUserMessage(...))` to feed the prompt back without a model round-trip). Adapt the prompt dir, command set, and file names to the host. Omit the schemastery dependency if the harness cannot resolve it (Config falls back to raw defaults).
