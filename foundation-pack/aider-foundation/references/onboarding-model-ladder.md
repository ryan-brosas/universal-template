<!-- capsule-v2 -->
# Onboarding model-selection ladder — key-scan → default pick → OpenRouter OAuth fallback

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When a first-time user launches with no model and possibly no keys, how does the CLI pick a working model without dead-ending?

## Scan env for known provider keys → propose a sensible default per found keys → if nothing, offer OpenRouter OAuth; persist tokens to ~/.aider/oauth-keys.env
**Path/Symbol:** `aider/onboarding.py`: `offer_openrouter_oauth(io, analytics)` (:15), OAuth device flow via `auth.aider.chat` endpoints (`POST /auth/v1/dev-server` :55, poll `/auth/v1/device/codes` :66-88, 5s interval, code expiry check :81), token persistence `~/.aider/oauth-keys.env` write (:117), `select_default_model(args, io, analytics)` (:135-427); consumer main.py :777-820 (re-offers OAuth when an openrouter/ model lacks its key).
**Signature:** `select_default_model` returns a model-name string or None (main exits 1); analytics events fired for every branch ("no model provided", "oauth selected", ...).
**Data Shape:** env scan order pins preferences: ANTHROPIC_API_KEY→sonnet, OPENROUTER_API_KEY→default openrouter model, else GEMINI_API_KEY→gemini/exp... with deepseek/azure/openai variants; unknown-key providers suggest gpt-4o-mini class fallbacks.

### Decisive source
```python
def select_default_model(args, io, analytics):
    if args.model is None:
        if os.environ.get("ANTHROPIC_API_KEY"):
            analytics.event("anthropic key found")
            return "sonnet"
        ...
        # no keys at all:
        if offer_openrouter_oauth(io, analytics):
            analytics.event("oauth selected")
            models_from_env = ...
```
OAuth loop: `while True: time.sleep(5); response=...device/codes...` until `code.has_expired` or user completes browser auth; success writes
`OPENROUTER_API_KEY=sk-or-...` into oauth-keys.env which load_dotenv_files() later inserts FIRST in the search order.

**Flow:** launch → select_default_model consults explicit --model first → env-key ladder → full OAuth onboarding → main re-checks openrouter/-prefixed selections and can re-run offer_openrouter_oauth mid-bootstrap (:792) before Model() construction.
**Invariant:** the OAuth file is written even when empty of comments — format must stay parseable by dotenv; every decline/failure path returns None so main() can exit 1 with guidance instead of constructing a broken Model.
**Probe:** deterministic anchors: `grep -nF 'oauth-keys.env' aider/onboarding.py aider/main.py | head -2` → onboarding write + main insert-at-0; `grep -nF 'select_default_model' aider/main.py` → :34 import + :777 call. Direct tests executed GREEN this run via repo venv (`python -m pytest tests/basic/test_onboarding.py -q`: **30 passed**; pins the env-ladder choices incl. oauth path mocks).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "offer_openrouter_oauth", limit: 3 });
// resolves offer_openrouter_oauth/select_default_model in aider/onboarding.py
```

## Verdict
Adopt the three-rung ladder (explicit → env-scan → OAuth) verbatim for any tool that needs a working LLM credential on first run; adapt provider table. The oauth-keys.env round-trip (onboarding writes, config-loader promotes) is the seam porters split incorrectly across modules.
