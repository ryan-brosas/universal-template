<!-- capsule-v2 -->
# AI model resolution ladder — availability-gated, plan-ranked fallback ending in a hard error

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How does a multi-provider chat product pick a model when the user's choice, their plan, and provider configuration can each independently invalidate it?

## Resolver + registry + descriptor triad
**Path/Symbol:** `packages/Chat/src/Services/AiModelResolver.php` (`pick` :32-48, `autoPick` :50-70); `ModelRegistry.php` (`__construct` :15-24, `autoChain` :89-98, `multiplierFor` :100-109, `customFromConfig` :112-134); `Support/ModelDescriptor.php` (`isAvailable` :47-59, `allowedForPlan` :61-64).
**Signature:** `resolve(User, ?string $override): array{provider: ?string, model: ?string}`; `ModelDescriptor::fromConfig(array): self`.
**Data Shape:** Curated entries `{id,label,provider,model,min_plan,credit_multiplier,supports_tools,write_guard,self_hosted}` from `config('chat.models')`; synthesized `selfhosted:<tag>` ids from `SELF_HOSTED_AI_URL` + comma-separated `SELF_HOSTED_AI_MODELS`; preference stored at `users.ai_preferences['default_model']`, sentinel value `'auto'`.

### Decisive source
```php
foreach ($chain as $descriptor) {
    if ($descriptor->isAvailable() && $descriptor->allowedForPlan($plan)) return $descriptor;
}
foreach ($chain as $descriptor) {
    if ($descriptor->isAvailable()) return $descriptor; // self-hosted infra is not plan-gated
}
return $this->registry->find('claude-sonnet') ?? $chain[0] ?? $this->registry->all()[0]
    ?? throw new RuntimeException('No chat model is configured; set at least one provider in config/chat.php.');
```
```php
// Servable on this install: tool-capable, has a model tag, and its provider
// connection is configured.
if (! $this->supportsTools || $this->model === null || $this->model === '') return false;
$connection = config("ai.providers.{$this->provider}", []);
return $this->selfHosted ? filled($connection['url'] ?? null) : filled($connection['key'] ?? null);
```

**Flow:** explicit override or stored preference is honored ONLY if `find()` succeeds AND `isAvailable()` AND `allowedForPlan(plan)` (plan rank ≥ min_plan rank) — anything else silently degrades to the auto chain instead of erroring → chain order comes from `chat.auto_chain` → final terminal state is a RuntimeException naming the config key. Registry merges curated + synthesized self-hosted models at construction; `multiplierFor(modelTag)` feeds credit metering and defaults to 1.0 for unknown tags.
**Invariant:** A user-facing picker option must never resolve to a request that will 401 or be rejected for tools: availability requires `supports_tools` AND a model tag AND a configured connection (cloud = API key present, self-hosted = base URL present). Plan gating applies to CLOUD cost tiers only — self-hosted capacity bypasses plan checks but keeps write_guard `'prompt'`. Unpriced/unknown model tags surface as "unpriced" in billing views, never silently zero-cost.
**Probe:** `tests/Feature/Chat/AiModelResolverTest.php` — 13 cases pin the ladder: disallowed preference falls back to Sonnet (:12-21), allowed Pro-plan Opus honored (:23-34), Gemini request reroutes to Sonnet (:52-61), Ollama honored when configured / falls back when not (:63-85), Auto→Ollama when NO cloud keys exist (:87-99) but Auto→Sonnet when both exist (:101-111), empty registry throws "No chat model is configured" (:155-167).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "AiModelResolver autoChain isAvailable allowedForPlan multiplierFor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way gate (capability × connectivity × entitlement) with a silent-degrade chain and a config-naming terminal error. Adapt Plan ranks and connection probing to your billing stack. Omit the specific curated catalog — it is product pricing, not a contract.
