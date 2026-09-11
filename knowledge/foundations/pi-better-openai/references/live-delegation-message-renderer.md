<!-- capsule-v2 -->
# Delegation message renderer — how do you render host-injected delegation chatter in a TUI without trusting the content shape?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** A voice session injects custom-typed "live request" messages into the agent transcript — how does the renderer extract text defensively and register itself against one stable custom type?

## Renderer registration
**Path/Symbol:** `src/live/index.ts:messageText` (:78-93), `registerMessageRenderer` wiring :310-314, constants `LIVE_COMMAND`/`LIVE_DELEGATION_MESSAGE_TYPE`/`LIVE_FOCUS_SETTLE_MS` :22-24; sibling command/shortcut dual-toggle :302-330.
**Signature:** `messageText(content: unknown): string`; `pi.registerMessageRenderer(LIVE_DELEGATION_MESSAGE_TYPE, (message, _options, theme) => Text)`.
**Data Shape:** Content is `unknown`: either a bare string or an array of `{type:"text", text:string}` records — anything else contributes nothing.

### Decisive source
```ts
function messageText(content: unknown): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((item): item is { type: "text"; text: string } =>
      typeof item === "object" && item !== null && "type" in item &&
      item.type === "text" && "text" in item && typeof item.text === "string")
    .map((item) => item.text)
    .join("\n");
}

pi.registerMessageRenderer(LIVE_DELEGATION_MESSAGE_TYPE, (message, _options, theme) => {
  const text = messageText(message.content).trim();
  const label = theme.fg("accent", theme.bold("Live request"));
  return new Text(`${label}\n${theme.fg("customMessageText", text)}`, 1, 0);
});
```

**Flow:** controller's `delegate()` sends a custom message (`customType: LIVE_DELEGATION_MESSAGE_TYPE`, `triggerTurn: true`, `deliverAs: "steer"` — activation capsule) → host persists it in the transcript → renderer fires per render for that type only → defensive extraction joins text items with newlines → theme-colored two-line block ("Live request" header + body). The same module registers `/live` (args must be empty, else usage error :319-322) and the visualizer toggle key (`ctrl+shift+l`) onto ONE shared `toggle` that finishes the active run's UI when already live (:302-308); `session_shutdown` tears down via `stopActive()` (:340-343).
**Invariant:** The renderer never throws on malformed content — every item is shape-checked before use and non-conforming shapes degrade to an empty body under the label, never a crash; rendering is keyed by the exported custom-type constant so producer and renderer cannot drift; command and shortcut are two entries into one toggle path (no divergent start/stop logic).
**Probe:** `tests/live-registration.test.ts` (:171 `commands.has("live")` after registration; :173 shortcut literal `"ctrl+shift+l"`; :174 recorded renderers contain `LIVE_DELEGATION_MESSAGE_TYPE`). Caveat: the Text-body construction itself has no behavioral test — registration contract only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "messageText registerMessageRenderer LIVE_DELEGATION_MESSAGE_TYPE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt unknown-shaped content extraction with per-item narrowing plus constant-keyed renderer registration. Adapt the TUI node/theme calls to your toolkit. Omit pi ExtensionAPI specifics unless targeting pi.
