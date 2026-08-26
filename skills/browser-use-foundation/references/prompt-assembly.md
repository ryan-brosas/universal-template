<!-- capsule-v2 -->
# Prompt assembly — template matrix + cacheable-prefix message layout

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does the per-step prompt stay provider-adapted, prompt-cache-friendly, and token-bounded while packing DOM state, history, files, and images into one message?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/prompts.py` (600 lines): `SystemPrompt` (:28-101) — template selection matrix (:60-92) over `{flash_mode, use_thinking, is_anthropic, is_browser_use_model}` picking one of 8 markdown templates from `agent/system_prompts/` via `importlib.resources`; Anthropic-4.5 detection forces 4096+ char prompts (cache minimum); `AgentMessagePrompt` (:104+) — `_extract_page_statistics` (:150), `_get_browser_state_description` (:224), `get_user_message` (:404-470).
**Signature:** system prompt = static template + `{max_actions}` interpolation, built ONCE (`cache=True`); user message = tagged sections in fixed order: `<agent_history>` → `<agent_state>` → `<browser_state>` → `<read_state>` (only if non-empty) → `<page_specific_actions>` → step metadata LAST.
**Data Shape:** page stats dict `{links, iframes, shadow_open/closed, scroll_containers, images, interactive_elements, total_elements, text_chars}`; clickable-elements text hard-capped at 40k chars.

### Decisive source
```ts
# template matrix: 8 variants by model family & capability
if self.is_browser_use_model:      # fine-tuned models get minimal prompts
    template = flash/thinking/no_thinking variant
elif self.is_anthropic_4_5 and flash_mode: 'system_prompt_anthropic_flash.md'
#   ^ Anthropic 4.5 needs 4096+ TOKEN prompts for prompt caching to engage!
# get_user_message layout — everything varying goes to the TAIL:
state_description += self._get_step_meta_description()   # step counter, date -> tail
# so the whole prefix is stable across steps = prompt-cache hits
# vision gating:
if is_new_tab_page(self.browser_state.url): use_vision = False  # placeholder screenshots
screenshots = [s for s in self.screenshots if s != PLACEHOLDER_4PX_SCREENSHOT]
# multimodal assembly: [text] + sample_images + labeled screenshots
# ('Current screenshot:' vs 'Previous screenshot:'), resized to llm_screenshot_size
```

**Flow:** agent constructs both prompts once per run for the system message, fresh each step for the user message → state sections rendered from live DOM/history/files → surrogate sanitization → if vision: text part + labeled screenshot parts (resized) else plain text → per-step metadata (step number/date) deliberately placed last so the entire preceding prefix stays byte-identical across steps and lands in the provider's prompt cache.
**Invariant:** the system message never changes mid-run (cacheable); variable content is segregated to the message tail; empty sections are omitted entirely (no `<read_state></read_state>` noise); new-tab pages skip vision (placeholder screenshots would poison the model); element lists are length-capped before rendering.
**Probe:** prompt tests assert template selection per model family; cache-prefix stability is structural (step meta appended last).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "SystemPrompt AgentMessagePrompt get_user_message flash_mode cache step_meta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the template-matrix system prompt and tail-segregated volatile content for cache-stable per-step messages; adapt template set and caps to host.
