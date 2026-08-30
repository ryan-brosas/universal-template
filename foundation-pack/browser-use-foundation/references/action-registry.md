<!-- capsule-v2 -->
# Action registry — decorator-registered tools compiled into per-page union schemas

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an agent expose ONLY the tools valid for the current page to the LLM, with secrets substituted at execution time?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/registry/service.py` (611 lines): `Registry` (:33) — `action` decorator (:291), `execute_action` (:331), `_create_param_model` (:275, builds a pydantic model from a function signature), `create_action_model` (:517-604), `_replace_sensitive_data` (:427, recursive placeholder substitution), `get_prompt_description` (:605); views in `tools/registry/views.py` (`RegisteredAction {domains, param_model, description}`).
**Signature:** `@registry.action('description', domains=['*.example.com'])` registers any async fn; `create_action_model(include_actions?, page_url?)` dynamically builds `Union[OneActionModel, ...]` containing ONLY domain-matched actions; each individual model has exactly ONE field so the LLM fills a single action per call.
**Data Shape:** registered actions carry optional `domains` filters; sensitive values live as `"<secret>:name"` placeholders in prompts and are substituted only inside `execute_action`.

### Decisive source
```ts
def create_action_model(self, include_actions=None, page_url=None):
    # filter: no page_url -> only unfiltered actions; else domain-match
    if page_url is None:
        if action.domains is None: available_actions[name] = action
    else:
        if self.registry._match_domains(action.domains, page_url): ...
    # one field per model: forces the LLM to pick ONE action per response
    individual_model = create_model(f'{name.title()...}ActionModel', __base__=ActionModel,
        **{name: (action.param_model, Field(description=action.description))})
    return Union-discriminated ActionModelUnion(RootModel)
# secret flow: LLM sees '<secret>:api_key' -> execute_action substitutes real value
#   via recursively_replace_secrets BEFORE calling the handler, logs usage
```

**Flow:** user decorates functions → param models generated from signatures (`_create_param_model`) → each step, the agent calls `create_action_model(page_url=current)` → schema sent to the LLM contains only this page's legal actions → LLM returns one filled model → `execute_action` matches it, substitutes secret placeholders recursively (dicts/lists included), logs sensitive usage, runs the handler.
**Invariant:** the LLM can never emit an action invalid for the current domain (schema-level enforcement, not prompt-level); exactly one action per turn; real secret values never appear in any prompt or message history.
**Probe:** `tests/` registry tests (domain filtering; dynamic union schema; secret replacement in nested params; excluded actions hidden).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "Registry action create_action_model _replace_sensitive_data domains param_model", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the decorator tool registry compiling to per-page discriminated unions + execution-time secret substitution — schema-enforced action validity beats prompting. Adapt domain matching to host.
