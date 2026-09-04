<!-- capsule-v2 -->
# Terminal focus via private mode 1004 — how do you learn the user's focus state without a GUI API?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How does a CLI app detect terminal window focus-in/out, and how does it degrade when the terminal doesn't support it?

## Focus reporting
**Path/Symbol:** `src/live/focus.ts` whole (:11-92); sequences :11-15.
**Signature:** `probeFocusReporting(handle, timeoutMs=400): Promise<boolean>`; `attachFocusReporting(handle, onFocus): () => void`; parsers `parseFocusSequence(data): boolean|undefined`, `parseDecrqmFocusResponse(data): boolean|undefined`.
**Data Shape:** Enable `CSI ? 1004 h`; the terminal then emits `CSI I` (focus-in) / `CSI O` (focus-out) AS INPUT; support is detected with DECRQM `CSI ? 1004 $ p` → response `CSI ? 1004 ; <Pm> $ y` where 1/3=set, 2/4=reset.

### Decisive source
```ts
export function parseDecrqmFocusResponse(data: string): boolean | undefined {
  if (data === "\x1b[?1004;1$y" || data === "\x1b[?1004;3$y") return true;
  if (data === "\x1b[?1004;2$y" || data === "\x1b[?1004;4$y") return false;
  return undefined;
}
```
Probe (:36-64) races one input listener against an unref'd 400ms timer, settles once, consumes the matched response; attach (:66-92) enables reporting best-effort and its disposer removes the listener FIRST, then disables — each write try/caught so a torn-down tty never throws. The header comment pins support: iTerm2, kitty, WezTerm, Alacritty, foot, Windows Terminal, xterm.js, modern tmux.

**Flow:** probe (query→response or timeout) → if supported attach + enable → `CSI I/O` arrive as plain input frames → parse → `onFocused(bool)` → dispose disables reporting.
**Invariant:** Tristate honesty: `undefined` from both parsers means "not a focus frame", never coerced to false; terminals that ignore BOTH sequences simply fall back to FIFO floor policy (the arbiter's `focused===undefined` path); enable/disable are best-effort writes.
**Probe:** `tests/live-focus.test.ts` (:39 in/out-only recognition incl. DECRQM-response NOT matching parseFocusSequence, :48-50 all four `$y` responses).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "probeFocusReporting FOCUS_REPORTING_ENABLE parseFocusSequence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mode-1004 probe+attach with tristate parsing and graceful FIFO fallback. Adapt the timeout and what focus drives (here: mic floor preemption). Omit nothing else — this file is fully portable terminal craft.
