<!-- capsule-v2 -->
# ifbench-prompt-rotation — why does the instruction move around inside the prompt, and what does that cost on middle turns?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How is the cat directive positioned per turn, and how does the turn template guarantee the placement is actually observable?

## buildTurnPrompt
**Path/Symbol:** `packages/coding-agent/src/if-bench/protocol.ts` (`buildTurnPrompt`, `CAT_PLACEMENTS`) + `prompts/turn.md`.
**Signature:** `buildTurnPrompt({ turn, start?, actions, nyaMax }): TurnPrompt` with `placement = CAT_PLACEMENTS[(turn - 1) % 3]` (beginning → middle → end, repeating).
**Data Shape:** Template renders `{{#if catBefore/catMiddle/catAfter}}` blocks around `START <...>` and one-or-two `ACTIONS` lines; `actionsTail` omitted when empty.

### Decisive source
```ts
const placement = CAT_PLACEMENTS[(options.turn - 1) % CAT_PLACEMENTS.length]!;
const tokens = options.actions.map(encodeAction);
// A mid-prompt directive is only observable when actions surround it, so the
// action list splits in half around it.
const split = placement === "middle" ? Math.ceil(tokens.length / 2) : tokens.length;
```

**Flow:** Rotation defeats positional attention — a model cannot succeed by attending only to prompt edges because the directive sweeps beginning/middle/end. For `middle`, the opcode list splits in half so a real ACTIONS line precedes AND follows the directive (otherwise the "middle" directive would sit at the boundary and be indistinguishable from end-placement). Turn 1 additionally carries `START <state>`; later turns never do.
**Invariant:** Placement is a pure function of the 1-based turn number (reproducible across runs), and the middle split must keep non-empty token lists on both sides to make the position measurable.
**Probe:** `grep -nF 'CAT_PLACEMENTS[(' packages/coding-agent/src/if-bench/protocol.ts` → line `71` and `grep -nF 'Math.ceil(tokens.length / 2)' packages/coding-agent/src/if-bench/protocol.ts` → line `75`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildTurnPrompt CatPlacement catMiddle actionsTail rotation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt directive rotation + observability-gating split; adapt template engine; omit the START seeding nuance if your benchmark re-seeds every turn. Direct test: `if-bench.test.ts` "rotates the cat directive through the prompt…" asserting first.content starts with the directive, turn-2 has no START, and ACTIONS lines surround the middle directive.
