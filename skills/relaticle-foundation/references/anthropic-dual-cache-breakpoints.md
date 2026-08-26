<!-- capsule-v2 -->
# Anthropic dual cache breakpoints — how do you cache both the static prefix and the growing agent-loop transcript?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** When an LLM agent loop replays the whole conversation every step, where do prompt-caching breakpoints go so neither the static prefix nor the transcript is re-read at full price?

## providerOptions top-level cache_control = Anthropic automatic caching
**Path/Symbol:** `packages/Chat/src/Agents/CrmAssistant.php` :467 `providerOptions(Lab|string $provider)`, :502 `anthropicCachedSystemBlocks()`.
**Signature:** `providerOptions(): array<string,mixed>` — returned array is merged verbatim into the provider request body by laravel/ai (no gateway override layer).
**Data Shape:** Breakpoint #1 lives INSIDE the payload: `system` is a list of content blocks, block[0] carries `'cache_control' => ['type' => 'ephemeral']`. Breakpoint #2 is TOP-LEVEL: `'cache_control' => ['type' => 'ephemeral']` as a sibling of `system`, not nested in any block. Both gated by one flag `config('chat.anthropic_prompt_caching')`; disabled ⇒ NEITHER key present (`tool_choice` remains).

### Decisive source
```php
return [
    'system' => $blocks,
    'cache_control' => ['type' => 'ephemeral'],
];
```
(:520-523). Docblock :494-499 states the semantics: the top-level `cache_control` is Anthropic's *automatic* caching — it places a second breakpoint after the LAST block of the request and moves it forward as the conversation grows. Without it every step of a MaxSteps(15) loop re-reads the replayed messages at full price even though the static prefix was cached. Commit message measures claude-sonnet-4-6 over a 3-step loop with ~2.8k-token tool results: uncached input per step went 73/2945/5816 → 3/1/1.

**Flow:** build static blocks (tools+instructions, breakpoint #1) → attach top-level automatic-caching key (breakpoint #2 follows the tail) → laravel/ai merges options into body → each loop step re-reads only its own delta.
**Invariant:** The two breakpoints are DIFFERENT mechanisms wearing the same value shape: #1 pins a fixed prefix, #2 rides the last block. Porting only #1 (the pre-fix state) silently re-bills the transcript on every step. Observability depends on recording `usage.cacheReadInputTokens`/`cacheWriteInputTokens` on the stream.completed breadcrumb (`packages/Chat/src/Jobs/ProcessChatMessage.php` :230-235) because `usage.input_tokens` reports ONLY the uncached remainder.
**Probe:** `tests/Feature/Chat/SequentialWriteEnforcementTest.php` (:60-65 asserts BOTH `$options['system'][0]['cache_control']` and top-level `$options['cache_control']` are `['type'=>'ephemeral']`; :67-103 Http::fake asserts both survive into the real request body; :105-113 flag-off removes BOTH keys).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "providerOptions anthropicCachedSystemBlocks cache_control", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-mechanism pairing (static-prefix block marker + top-level auto-cache key) for ANY multi-step agent loop on Anthropic; adapt block construction to your prompt assembler; omit Relaticle's Lab/provider enum plumbing. Direct tests pin both presence and flag-off absence at request-body level.
