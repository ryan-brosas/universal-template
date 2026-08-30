<!-- capsule-v2 -->
# Provider health plane — patched Anthropic gateway and a retrieve-don't-generate liveness check

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you patch an LLM SDK's wire format without forking it, and health-check cloud providers without spending tokens or flapping?

## Driver swap + empty-argument coercion
**Path/Symbol:** `app/Ai/AiManager.php` (whole, 28L, `createAnthropicDriver(array $config): AnthropicProvider` returning a provider built around `App\Ai\Anthropic\AnthropicGateway`); gateway patch `app/Ai/Anthropic/AnthropicGateway.php` (whole, 47L, overrides `mapAssistantMessage(AssistantMessage|Message $message, array &$mapped)`); health check `app/Health/ChatProviderCheck.php` (whole, 176L, extends Spatie `Check`).
**Signature:** the patch walks the LAST mapped message; if its role is `assistant`, it maps every `tool_use` block and replaces empty array input with `(object) []`. The check is instantiated per provider by `forConfiguredProviders(): list<self>` from `config('chat.models')`.
**Data Shape:** upstream bug: `ToolCall::$arguments` is typed `array`, so empty JSON-object arguments round-trip to `[]`; Anthropic's Messages API rejects `tool_use.input` as a JSON array with a 400. Health-check config entry: `{provider, model, min_plan, supports_tools, self_hosted}`.

### Decisive source
```php
$mapped[$lastIndex]['content'] = array_map(
    static function (array $block): array {
        if (($block['type'] ?? null) === 'tool_use') {
            $input = $block['input'] ?? [];
            $block['input'] = is_array($input) && $input === [] ? (object) [] : $input;
        }
        return $block;
    },
    $mapped[$lastIndex]['content'],
);
```
The health check probes with `GET models/{model}` — never a generation call: "a reasoning model spends that budget on thinking before it emits anything. OpenAI rejects a budget under 16 … so no value both stays free and stays green at an every-minute cadence. A revoked key and a retired model — the two persistent faults this check exists to catch — are precisely what this endpoint reports, as 401 and 404."
```php
if ($response->status() === 429 || $response->serverError()) {
    return $result->warning("{$this->provider} is temporarily unavailable: …");
}
return $result->failed("{$this->provider} model '{$this->model}' is unavailable: …");
```
Status ladder: ok on 2xx; WARNING on 429/5xx/ConnectionException (transient, nothing actionable); FAILED on 401/404 and on an unknown provider (`probe()` returns null → "no health probe is defined for chat provider …" — fail loudly rather than report unprobed as healthy). The probe client mirrors how laravel/ai builds its own client per provider (`x-api-key`+`anthropic-version` for Anthropic, bearer token for OpenAI), so it fails for the same reasons a real chat turn would; `baseUrl()` honors a configured override.

**Flow:** container binds `App\Ai\AiManager` as the laravel/ai manager → every Anthropic turn's request body passes through the patched gateway → empty tool arguments serialize as `{}`. Separately, the health register builds ONE check per provider that has a key configured, targeting the free-plan model per provider (the one most turns actually use); self-hosted and `supports_tools=false` entries are excluded.
**Invariant:** SDK patches attach at the narrowest overridable seam (one message-mapping method) and stay upgrade-safe. Health checks must distinguish persistent faults (fail) from transient ones (warn) or alerting becomes noise; a provider the check cannot probe must FAIL, never pass silently; providers without keys are left unregistered rather than skipped, because a skipped check counts as a failure in Spatie Health reports.
**Probe:** `tests/Feature/AI/AnthropicGatewayEmptyToolInputTest.php` — manager binding asserted via reflection; empty input encodes to `"input":{}` and never `"input":[]`; non-empty dicts preserved; full request body asserted valid. `tests/Feature/HealthChecks/ChatProviderCheckTest.php` — exact headers/URLs per provider, `assertNotSent` for any generation request, base-url override, 429/529/timeout → warning, 404/401 → failed, unknown provider fails loudly with nothing sent, one check per keyed provider, catalogue-wide probeability.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "AnthropicGateway mapAssistantMessage tool_use input ChatProviderCheck forConfiguredProviders reachableModels", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the narrow-seam gateway override for any vendor wire-format bug, and the model-retrieve health probe for any metered LLM provider. Adapt the probe endpoint to your provider's cheapest read; keep the transient-vs-persistent status split and the fail-loud unknown-provider branch. Omit the driver swap if your SDK version already serializes empty objects correctly. Companion to `ai-model-resolution-ladder.md` (the catalogue this check reads).
