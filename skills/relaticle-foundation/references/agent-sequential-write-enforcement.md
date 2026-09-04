<!-- capsule-v2 -->
# Sequential-write enforcement — make the provider refuse parallel tool calls instead of trusting the prompt

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How do you guarantee an approval-gated agent cannot fire two write tools in one model turn, when the only real gate is a human clicking approve?

## Provider-level parallel-tool-use kill switch
**Path/Symbol:** `packages/Chat/src/Agents/CrmAssistant.php`: class attributes (:57-64), `providerOptions(Lab|string $provider)` (:467-484); `packages/Chat/src/Enums/WriteGuard.php` (whole, 12L); tool-side half: `meta.agent_should_stop` in every write envelope (`BaseWrite*Tool.php`).
**Signature:** `providerOptions(Lab|string $provider): array`
**Data Shape:** Anthropic → `['tool_choice' => ['type' => 'auto', 'disable_parallel_tool_use' => true], ...cachedSystemBlocks]`; OpenAI → `['parallel_tool_calls' => false]`; anything else → `[]`.

### Decisive source
```php
// Gemini is excluded until laravel/ai's Gemini driver hoists `tool_config`
// to the request top-level. Currently, providerOptions() values are merged
// into generationConfig, so Gemini's function_calling_config mode cannot be
// set via this mechanism — leaving the sequential-write guard unenforceable.
#[Provider(['anthropic', 'openai'])]
```
```php
return match ($providerKey) {
    Lab::Anthropic->value => [
        'tool_choice' => ['type' => 'auto', 'disable_parallel_tool_use' => true],
        ...$this->anthropicCachedSystemBlocks(),
    ],
    Lab::OpenAI->value => ['parallel_tool_calls' => false],
    default => [],
};
```

**Flow:** provider options disable parallel calls at the API boundary → static instructions add the behavioral layer ("After ANY write tool call, STOP your turn immediately") → each write tool result carries `meta.agent_should_stop: true` for the loop driver → if anything slips through anyway, the proposal gate means a second write just creates another pending card, not a second mutation. Per-model guard level is declared in config (`chat.models[*].write_guard` = `api|prompt`) and surfaced as `WriteGuard` enum: `Api` = provider-enforced, `Prompt` = prompt-only with the approval gate as the net.
**Invariant:** A provider that cannot enforce single-tool-per-turn must be EXCLUDED from the agent entirely, not trusted — Gemini is blocked via `supports_tools: false` in `chat.models` and the `#[Provider(['anthropic','openai'])]` allowlist, because its driver merges options into `generationConfig` where `function_calling_config` is unreachable. The three layers (API option, prompt rule, stop meta) are redundant by design; never collapse them into one.
**Probe:** `tests/Feature/Chat/SequentialWriteEnforcementTest.php` — asserts the live request body carries `tool_choice.disable_parallel_tool_use === true` (`Http::assertSent` :45-49), `providerOptions('openai') === ['parallel_tool_calls' => false]` and `'gemini' → []` (:52-58), a write tool's result has `meta.agent_should_stop === true` (:115-138), and instructions contain "STOP your turn immediately" plus the `[approval]` token (:140-150).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "providerOptions disable_parallel_tool_use WriteGuard agent_should_stop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt provider-native parallel-call disabling as the primary enforcement of human-in-the-loop write flows; adapt the enum vocabulary to your model catalog. Omit the specific laravel/ai driver caveat unless you target Gemini through this stack. Direct tests pin every branch including the exclusion rationale.
