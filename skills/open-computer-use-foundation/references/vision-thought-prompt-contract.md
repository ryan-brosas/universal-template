<!-- capsule-v2 -->
# Vision-thought prompt contract — how does the agent decide the objective is complete without a completion tool call?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How does the vision model's free-text output get structured so it doubles as screen description, completion check, and next-step plan?

## Fixed three-line response grammar enforced by prompt only
**Path/Symbol:** `os_computer_use/sandbox_agent.py:152-169` (`SandboxAgent.append_screenshot`).
**Signature:** `append_screenshot(self)` → `vision_model.call([*self.messages, Message([screenshot_bytes, prompt_text], role="user")])` → str.
**Data Shape:** Input message content is a LIST mixing raw PNG bytes (first element) and instruction text; output is unstructured text that downstream code treats as an opaque string (only `logger.log` consumes it — parsing is delegated to the ACTION model).

### Decisive source
```python
return vision_model.call([
    *self.messages,
    Message(
        [self.screenshot(),
         "This image shows the current display of the computer. Please respond in the following format:\n"
         "The objective is: [put the objective here]\n"
         "On the screen, I see: [an extensive list of everything that might be relevant to the objective including windows, icons, menus, apps, and UI elements]\n"
         "This means the objective is: [complete|not complete]\n\n"
         "(Only continue if the objective is not complete.)\n"
         "The next step is to [click|type|run the shell command] [put the next single step here] in order to [put what you expect to happen here].",
        ],
        role="user",
    ),
])
```

**Flow:** screenshot() → bytes embedded as first content element → history prepended so the vision model sees prior objectives/thoughts/observations → model returns the fixed-format assessment → the returned string is logged green as `THOUGHT: …` inside `run()` and becomes part of NEXT turn's action-model context.
**Invariant:** The completion decision lives in TEXT (`[complete|not complete]`) consumed by a second model, not in control flow — there is no parser and no schema; robustness comes from the strict line grammar plus the action model's freedom to emit `stop()` after reading it. A porter who adds JSON parsing here breaks the design's tolerance of chatty vision models.
**Probe:** `cd /mnt/hdd/utopia/inspo/external/open-computer-use && grep -n 'objective is' os_computer_use/sandbox_agent.py` → expect 4 hits (:160/:162/:163 grammar lines + :192 the action-model preamble "if the objective is complete"); `sed -n '152,169p' os_computer_use/sandbox_agent.py` for the verbatim prompt.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "append_screenshot vision current display objective", limit: 5, fields: ["signature", "name", "file"] });
// expect ext-open-computer-use.os_computer_use.sandbox_agent.SandboxAgent.append_screenshot
```

## Verdict
Adopt the describe→verdict→next-step text grammar when pairing a cheap vision model with a separate action model; adapt the exact wording to your models (the grammar is prompt-only, no validation exists); omit any expectation of machine-parseable completion — this seam deliberately trades structure for provider flexibility.
