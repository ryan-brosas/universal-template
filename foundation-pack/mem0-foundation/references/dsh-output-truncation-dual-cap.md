<!-- capsule-v2 -->
# dsh-mem0 output truncation — what stands between a huge recall and the context window?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** How do you cap tool output by BOTH lines and bytes while still telling the model what was dropped?

## Dual-cap truncation kernel
**Path/Symbol:** `integrations/dsh-mem0/src/output.ts` (`truncateOutput`, lines 12-33; caps exported at :9-10).
**Signature:** `truncateOutput(text: string): string` with `MAX_OUTPUT_LINES = 200`, `MAX_OUTPUT_BYTES = 50_000`.
**Data Shape:** pass-through when under both caps; else line-slice → byte-slice of the KEPT region → `\n\n[Output truncated: …]` notice listing each reason that fired.

### Decisive source
```ts
if (lines.length <= MAX_OUTPUT_LINES && text.length <= MAX_OUTPUT_BYTES) return text;
const kept = lines.slice(0, MAX_OUTPUT_LINES);
let result = kept.join("\n");
const byteCapped = result.length > MAX_OUTPUT_BYTES;
if (byteCapped) result = result.slice(0, MAX_OUTPUT_BYTES);
const dropped = lines.length - kept.length;
if (dropped > 0) reasons.push(`showing ${kept.length} of ${lines.length} lines`);
if (byteCapped) reasons.push(`cut at ${Math.floor(MAX_OUTPUT_BYTES / 1000)}KB`);
result += `\n\n[Output truncated: ${reasons.join(", ")}]`;
```

**Flow:** under both caps → return untouched → else slice lines to 200 → if the kept text still exceeds 50,000 chars, byte-slice it → append a combined-reason notice.
**Invariant:** Both tools route EVERY output (success AND failure strings) through this guard before returning — no path can flood the context window in one call. The byte cap is applied AFTER the line cap so the two caps compose; the notice is appended AFTER slicing so the model always sees WHY output ended. Caps live in shared constants because the sibling family pins the identical values (`integrations/pi-agent-plugin/src/memory/tools.ts` :17-18) — treat 200/50KB as the family contract, not tunables to drift.
**Probe:** `integrations/dsh-mem0/tests/output.test.ts` (few-lines-but-huge single-line 60KB input is byte-capped with notice; wide input fires BOTH reasons incl. literal `cut at 50KB`; small output passes through byte-identical) — green offline.
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `truncateOutput` limit 3 → `integrations.dsh-mem0.src.output.truncateOutput` output.ts 12-33 rank 1 line-exact.

## Verdict
Adopt the dual-cap composition order (lines then bytes) and the machine-readable trailing notice; adopt the constants as-is for cross-plugin parity. Adapt the notice wording to your host's conventions. Omit streaming/pagination alternatives — the family deliberately ships one-shot capped text.
