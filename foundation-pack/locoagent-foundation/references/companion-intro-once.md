<!-- capsule-v2 -->
# Companion intro attachment — how do you announce a persistent UI side-character to the LLM exactly once, without polluting every turn?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a companion/side-character sits beside the user's input box and can be addressed BY NAME in any user message, how does the LLM learn its existence — a permanent system-prompt paragraph (wasted tokens every turn) or an idempotent one-shot attachment?

## Path/Symbol
`src/buddy/prompt.ts`: `companionIntroText` (`:7-13`), `getCompanionIntroAttachment` (`:15-36`). Companion resolution: `getCompanion()` (`src/buddy/companion.ts`, see companion-generation capsule). Feature gate: `feature('BUDDY')` from `src/_stubs/bun-bundle.js`.

**Signature:** `companionIntroText(name: string, species: string): string`; `getCompanionIntroAttachment(messages: Message[] | undefined): Attachment[]`.

**Data Shape:** Returns either `[]` (no announcement owed) or exactly one attachment `{ type: 'companion_intro', name, species }`. The dedup key inside history is the attachment's `name` field. Gating inputs: `feature('BUDDY')`, `getCompanion()`, `getGlobalConfig().companionMuted`.

### Decisive source
```ts
export function getCompanionIntroAttachment(
  messages: Message[] | undefined,
): Attachment[] {
  if (!feature('BUDDY')) return []
  const companion = getCompanion()
  if (!companion || getGlobalConfig().companionMuted) return []

  // Skip if already announced for this companion.
  for (const msg of messages ?? []) {
    if (msg.type !== 'attachment') continue
    if (msg.attachment.type !== 'companion_intro') continue
    if (msg.attachment.name === companion.name) return []
  }

  return [
    {
      type: 'companion_intro',
      name: companion.name,
      species: companion.species,
    },
  ]
}
```
(Excerpt elides one line of the loop; source range `:15-36` is authoritative.)

And the intro text itself (`:8-12`) — the anti-persona boundary is IN the prompt:
```text
A small ${species} named ${name} sits beside the user's input box … You're not
${name} — it's a separate watcher. When the user addresses ${name} directly …
respond in ONE line or less … Don't explain that you're not ${name} — they know.
Don't narrate what ${name} might say — the bubble handles that.
```

## Flow
1. Each turn build, the caller passes conversation history; the function re-derives whether an intro is OWED right now.
2. Four gates run in order: feature off → no companion → user muted the companion → **already announced**: scan history for ANY prior `type === 'attachment'` message with `attachment.type === 'companion_intro'` whose `name` equals the CURRENT companion's name.
3. Only when all four pass does the caller append the single `companion_intro` attachment; `companionIntroText(name, species)` renders its prose.
4. Renaming the companion flips the dedup key (`name`), so a renamed companion is legitimately re-announced — intended.

**Invariant:** The announcement is DERIVED from history at turn-build time, never persisted as a "was introduced" flag anywhere — stateless idempotence. That means history truncation/compaction can silently re-trigger an intro (harmless duplicate), whereas a persisted flag would suppress the intro after compaction ate the announcement (the harmful direction). Muting must gate BEFORE the history scan so a muted companion never re-announces from stale history. The prose hard-splits responsibilities: main model answers in ≤1 line when the user addresses the companion; it must NOT roleplay or narrate the companion.

## Probe
No direct test file exists for `src/buddy/prompt.ts` (coverage caveat — source-grounded probe). Deterministic checks: grep pins `feature('BUDDY')` at `src/buddy/prompt.ts:18`, `companionMuted` at `:20`, and the `name ===` dedup comparison at `:26`; the `companion_intro` type is declared alongside `Message`/`Attachment` types in the upstream corpus and consumed only here.

**Retrieve:** `search_graph --project locoagent --query "getCompanionIntroAttachment"` → `locoagent.src.buddy.prompt.getCompanionIntroAttachment` Function `src/buddy/prompt.ts 15-36`; `trace_path --function-name getCompanionIntroAttachment` shows callees `getCompanion`/`roll`/`hashString`/`mulberry32` (the deterministic bones pipeline) plus `tail-agent.watchFile`.

**Verdict:** Adopt. The once-per-companion derived-from-history attachment pattern ports to any agent that injects context about a persistent side-channel (watchers, background daemons, second persona): derive "already said" from history each turn instead of storing introduction flags, and put the stay-out-of-the-way rules in the intro itself.
