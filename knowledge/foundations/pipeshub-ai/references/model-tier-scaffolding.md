<!-- capsule-v2 -->
# Model-tier prompt scaffolding — how much scaffolding should the system prompt add for each capability class, and where do local models get classified?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** one prompt template serves frontier, mid, and quantized-local models — how is the tier resolved and what does each tier change?

## Frozen profile snapshot with conservative fallback
**Path/Symbol:** `backend/python/app/agents/agent_loop/model_tier.py:34-117` (`ModelTier`, `ModelProfile.resolve` :51-86, `inject_traces` :96-103, `UNKNOWN_PROFILE` :111).
**Signature:** `ModelProfile.resolve(*, provider, model_name, context_length: int | None, is_reasoning: bool) -> ModelProfile` (frozen dataclass); thresholds `_SMALL_MAX_CONTEXT=32_768`, `_MID_MAX_CONTEXT=131_072`.
**Data Shape:** tier ∈ {frontier, mid, small}; provider compared lowercased against frozenset {"ollama","lmstudio","lm_studio"}.

### Decisive source
```python
ctx = context_length if context_length and context_length > 0 else 8_192

if is_reasoning:
    tier = ModelTier.FRONTIER
elif provider_lower in _LOCAL_PROVIDERS:
    tier = ModelTier.SMALL
elif ctx <= _SMALL_MAX_CONTEXT:
    tier = ModelTier.SMALL
elif ctx <= _MID_MAX_CONTEXT:
    tier = ModelTier.MID
else:
    tier = ModelTier.FRONTIER
...
def inject_traces(self) -> bool:
    """SMALL models are excluded: they confuse the example format with an
    instruction and emit ``TOOL tool_name | param=...`` as literal text
    instead of making actual function calls (see gemma4 regression)."""
    return self.tier == ModelTier.MID
```

**Flow:** resolve once per request into an immutable snapshot → prompt builder asks three predicates (is_small / inject_traces / inject_expanded_rubrics) to pick scaffolding level.
**Invariant:** reasoning models clamp to FRONTIER regardless of context window; LOCAL PROVIDERS ARE ALWAYS SMALL regardless of reported context (quantized inference dominates any advertised size); unknown/missing context falls back to 8k ⇒ SMALL (conservative). Traces go to MID ONLY — SMALL mimics example format as literal text (gemma4 regression), so worked examples are actively harmful there; rubrics go to SMALL+MID.

### Direct test
**Probe:** no dedicated unit suite — classify_error-style table test absent by design (pure classification). Deterministic anchor: `grep -c 'def ' app/agents/agent_loop/model_tier.py` = 6; boundary assertions live in prompt-builder wiring. Execute from repo root `backend/python`: `grep -c '_LOCAL_PROVIDERS' app/agents/agent_loop/model_tier.py` → 2.
Coverage caveat recorded honestly: this capsule's Probe is a deterministic grep + docstring-pinned regression note, NOT a runner test — the only plane module without a direct suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "ModelProfile resolve tier context_length frontier small", limit: 3, fields: ["signature", "name", "file"] });
// resolves model_tier.py Methods line-exact (resolve 51-86, is_small 89-90, is_frontier 93-94)
```

## Verdict
Adopt tier-gated scaffolding with the four classification rules (reasoning-clamp, local-always-small, window thresholds, conservative 8k fallback) and the traces-are-mid-only regression lesson. Adapt thresholds to your model roster. Omit PipesHub etcd config sourcing.
