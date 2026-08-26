<!-- capsule-v2 -->
# Skills command degradation ladder — headless notify fallback and a try/catch around the custom-UI mount keep /memory-skills usable in every runtime

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** The same command must work in a full TUI, a headless child process, and a host whose custom-UI API lies about being available — how do you structure the entrypoint so each environment gets the best surface it actually supports?

## registerSkillsCommand
**Path/Symbol:** `src/handlers/skills-command.ts:registerSkillsCommand` (:1261–1334); inventory probe `getSkillCommands` with duck-typed `readCommands(owner)` (:1265–1280); headless gate `!ctx.hasUI || typeof ctx.ui.custom !== "function"` (:1287–1290); interactive mount `ctx.ui.custom<void>(...)` with overlay options (:1293–1319); catch-path re-collect + double notify (:1320–1331); static twin `formatSkillsList` (:269–324).
**Signature:** `registerSkillsCommand(pi: ExtensionAPI, store: SkillStore): void`; handler `async (_args, ctx) → void`.
**Data Shape:** runtime external-skill inventory = commands where `source === "skill"`; read via `(owner as {getCommands?}).getCommands` guarded by `typeof getter === "function"`, wrapped in its own try/catch returning `null` so a THROWING registry degrades to `[]`, tried on `pi` first then `ctx`.

### Decisive source
```ts
if (!ctx.hasUI || typeof ctx.ui.custom !== "function") {
  ctx.ui.notify(formatSkillsList(initialRows, projectName), "info");
  return;
}
try {
  await ctx.ui.custom<void>(/* SkillsManagerModal factory + overlay options */);
} catch {
  const latestManagedSkills = await store.loadIndex();        // RE-READ after the failed mount
  const latestRows = buildUnifiedSkills(latestManagedSkills, collectLoadedSkillsFromCommands(getSkillCommands()));
  ctx.ui.notify("Interactive skills manager unavailable in this runtime; showing read-only list fallback.", "warning");
  ctx.ui.notify(formatSkillsList(latestRows, projectName), "info");
}
```
`formatSkillsList` renders the SAME [G]/[P]/[E] grouped layout as the modal (legend line, per-skill description + id), and the empty state tells the user HOW to create skills ("Ask the agent to save a reusable procedure…") instead of just saying empty (:282–288).

**Flow:** collect managed index + runtime loaded rows → build unified rows ONCE → branch by capability → interactive path wires callbacks (`moveSelected`/`deleteSelected`/`close: () => done(undefined)`) over the SAME pure batch functions used everywhere else. The catch path deliberately RE-COLLECTS both inventories because time passed during the failed mount attempt.
**Invariant:** the capability check tests presence AND callability of `ui.custom` — a porter checking only `hasUI` crashes in hosts that advertise UI but lack the custom-modal API (the test suite builds exactly such a lying host). The static renderer is shared by BOTH branches so the two surfaces can never drift apart.
**Probe:** `tests/handlers/skills-command.test.ts` — "falls back to notify output when custom UI is unavailable" (:594, severity info), "gracefully handles getCommands errors without custom UI" (:651, throwing pi.getCommands still yields the list), "opens custom modal even when getCommands throws" (:719).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "registerSkillsCommand formatSkillsList getSkillCommands hasUI", limit: 5 })`

## Verdict
Adopt for any extension command exposing an optional rich UI. Adapt overlay geometry; keep the callable-check gate, the throwing-inventory tolerance, the warning+info double notify, and the post-failure re-collection. Omit nothing.
