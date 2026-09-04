<!-- capsule-v2 -->
# clarified-gen-swap — How does a clarification Q&A become the codegen context, and what gets swapped?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What terminates the clarify loop and how is the transcript reused for generation?

## Clarify-then-generate seam
**Path/Symbol:** `gpt_engineer/tools/custom_steps.py:clarified_gen` (:122-195); termination tokens from `gpt_engineer/preprompts/clarify`.
**Signature:** `clarified_gen(ai, prompt: Prompt, memory, preprompts_holder) -> FilesDict`.
**Data Shape:** Grows one message list through Q&A, then SURGICALLY mutates message[0] and continues — no fresh conversation.

### Decisive source
```python
messages = [SystemMessage(content=preprompts["clarify"])]
user_input = prompt.text
while True:
    messages = ai.next(messages, user_input, step_name=curr_fn())
    msg = messages[-1].content.strip()
    if "nothing to clarify" in msg.lower(): break
    if msg.lower().startswith("no"): print("Nothing to clarify."); break
    user_input = input("")
    if not user_input or user_input == "c":
        messages = ai.next(messages, "Make your own assumptions and state them explicitly before starting", step_name=curr_fn())
    user_input += "\n\nIs anything else unclear? If yes, ask another question.\nOtherwise state: \"Nothing to clarify\""
...
messages = [SystemMessage(content=setup_sys_prompt(preprompts))] + messages[1:]  # skip clarify priming
messages = ai.next(messages, preprompts["generate"].replace("FILE_FORMAT", preprompts["file_format"]), ...)
```

**Flow:** clarify-system prime → loop (ask → user answers | "c"/empty ⇒ assumption directive) until "nothing to clarify" or "no…" prefix → REPLACE message[0] (clarify prime) with full generation system prompt, KEEPING entire Q&A tail → issue generate instruction as next user turn → parse files.
**Invariant:** (1) Termination is SUBSTRING match "nothing to clarify" case-insensitive OR reply STARTING with "no" — the latter risks premature exit if a question begins "No..." but is the documented shortcut. (2) The swap preserves conversation continuity: all clarifications remain in context when code is written (spec knowledge transfers); only the priming persona changes. (3) Vision disabled: uses prompt.text, dropping image_urls (comment says clarify doesn't work with vision yet). (4) Interactive input is REQUIRED — headless ports need a scripted answer provider. (5) After swap, the generate preprompt rides as a USER message, unlike plain gen_code where it's inside the system prompt.
**Probe:** `grep -n 'skip the first clarify message' gpt_engineer/tools/custom_steps.py` → :185 (the swap comment).
**Probe:** `grep -ci 'nothing to clarify' gpt_engineer/tools/custom_steps.py` → 3 (:152 break check lowercase, :156 print, :176 appended instruction — case-insensitive because the terminator string appears capitalized in prose).
**Probe:** `cat gpt_engineer/preprompts/clarify` → ends with 'Otherwise state: "Nothing to clarify"' — the trained terminator.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "clarified_gen nothing to clarify assumptions messages", limit: 10 });
```

## Verdict
Adopt transcript-reuse-with-persona-swap for spec-then-build pipelines; adapt termination tokens to your model's dialect (make them stricter); omit interactive input() in favor of injected answer callbacks. lite_gen (same file :198-233) is the degenerate no-clarify variant worth carrying alongside.
